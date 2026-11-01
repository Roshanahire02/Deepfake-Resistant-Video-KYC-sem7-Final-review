"""
Fine-tune EfficientNet-B0 as a real/fake face classifier (Model E).

    python train_deepfake_model.py --data /data/deepfake_frames --epochs 5 \
        --out ../../backend/storage/models/deepfake_effnet.pt

Needs: torch, torchvision, scikit-learn, pillow  (a GPU is strongly recommended
-- use Colab/Kaggle; CPU works only for very small experiments).

Design choices that keep the numbers honest:
  * Frames are grouped by their `<videoid>__` filename prefix and split by
    GROUP (70/15/15) -- no video appears in more than one split (no leakage).
  * Best epoch is picked on the VALIDATION set; the TEST set is evaluated
    exactly once at the end.
  * Metrics (accuracy/precision/recall/F1/ROC-AUC/confusion matrix) are
    written to <out>.metrics.json. The backend's /api/system/models reads
    that file; with no file it says "Not evaluated yet". Nothing is invented.
  * The checkpoint is a plain state_dict whose layout matches
    backend/app/ml/deepfake.py::_load_model (classifier[1] = Linear(in, 2),
    class 1 = FAKE), and inputs use the same preprocessing as inference.

Datasets (obtain yourself, respect each licence): FaceForensics++, Celeb-DF,
DFDC. Metrics describe THIS dataset's test split only -- never claim
real-world deepfake-detection performance from them.
"""
import argparse
import json
import os
import random
import sys

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import efficientnet_b0

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evaluation"))
from data_split import group_split, list_samples  # noqa: E402
from metrics import classification_metrics  # noqa: E402

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]  # identical to the backend's preprocess_frame


class FrameDataset(Dataset):
    def __init__(self, samples, train):
        aug = [transforms.RandomHorizontalFlip(), transforms.ColorJitter(0.2, 0.2, 0.2)] if train else []
        self.t = transforms.Compose([transforms.Resize((224, 224)), *aug, transforms.ToTensor(), transforms.Normalize(MEAN, STD)])
        self.samples = samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label, _ = self.samples[i]
        return self.t(Image.open(path).convert("RGB")), label


def build_model():
    m = efficientnet_b0(weights="IMAGENET1K_V1")
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, 2)
    return m


@torch.no_grad()
def predict(model, loader, device):
    model.eval()
    probs, labels = [], []
    for x, y in loader:
        p = torch.softmax(model(x.to(device)), dim=1)[:, 1].cpu().numpy()
        probs.extend(p.tolist())
        labels.extend(y.numpy().tolist())
    return np.array(labels), np.array(probs)


def metrics(y, p):
    return classification_metrics(y, p, threshold=0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="../../backend/storage/models/deepfake_effnet.pt")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--dataset-name", default="unspecified", help="recorded in the metrics file, e.g. 'FaceForensics++ c23 subset'")
    a = ap.parse_args()

    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_s, val_s, test_s = group_split(list_samples(a.data))
    print(f"device={device}  train={len(train_s)} val={len(val_s)} test={len(test_s)} frames (split by video, no leakage)")

    mk = lambda s, tr: DataLoader(FrameDataset(s, tr), batch_size=a.batch_size, shuffle=tr, num_workers=a.workers)
    train_l, val_l, test_l = mk(train_s, True), mk(val_s, False), mk(test_s, False)

    model = build_model().to(device)
    labels = np.array([s[1] for s in train_s])
    w = torch.tensor([len(labels) / (2 * max((labels == c).sum(), 1)) for c in (0, 1)], dtype=torch.float32, device=device)
    loss_fn = nn.CrossEntropyLoss(weight=w)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)

    best_auc, best_state = -1.0, None
    for ep in range(1, a.epochs + 1):
        model.train()
        total = 0.0
        for x, y in train_l:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            total += loss.item() * len(y)
        yv, pv = predict(model, val_l, device)
        m = metrics(yv, pv)
        score = m["roc_auc"] if m["roc_auc"] is not None else m["accuracy"]
        print(f"epoch {ep}: train_loss={total/len(train_s):.4f}  val_acc={m['accuracy']:.4f}  val_auc={m['roc_auc']}")
        if score > best_auc:
            best_auc = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    yt, pt = predict(model, test_l, device)  # TEST evaluated once, after model selection
    test_m = metrics(yt, pt)
    print("TEST:", json.dumps(test_m, indent=2))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    torch.save(best_state, a.out)
    with open(a.out + ".metrics.json", "w") as f:
        json.dump({"dataset": a.dataset_name, "split": "by video (70/15/15), no leakage", "test": test_m,
                   "note": "Metrics describe this dataset's test split only, not real-world performance."}, f, indent=2)
    print(f"Saved checkpoint -> {a.out}\nSaved metrics    -> {a.out}.metrics.json")


if __name__ == "__main__":
    main()
