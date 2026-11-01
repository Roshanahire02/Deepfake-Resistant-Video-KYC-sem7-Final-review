import PageHeader from '../../components/PageHeader'
import CaseQueue from '../../components/reviewer/CaseQueue'

export default function ReviewerQueue() {
  return (
    <div>
      <PageHeader title="Review Queue" breadcrumb={<span className="mono text-[11px] uppercase tracking-wider text-brand">Reviewer Console</span>} description="Cases awaiting a reviewer decision." />
      <CaseQueue title="Pending Review" defaultFilter="pending" />
    </div>
  )
}
