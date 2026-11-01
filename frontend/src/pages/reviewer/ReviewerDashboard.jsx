import PageHeader from '../../components/PageHeader'
import CaseQueue from '../../components/reviewer/CaseQueue'

export default function ReviewerDashboard() {
  return (
    <div>
      <PageHeader
        title="Fraud Review Command Center"
        breadcrumb={<span className="mono text-[11px] uppercase tracking-wider text-brand">Reviewer Console</span>}
        description="AI-assisted triage of identity verification cases. AI output is a recommendation; the reviewer makes the final decision."
      />
      <CaseQueue showKpis />
    </div>
  )
}
