import PageHeader from '../../components/PageHeader'
import CaseQueue from '../../components/reviewer/CaseQueue'

export default function ReviewerCases() {
  return (
    <div>
      <PageHeader title="All Cases" breadcrumb={<span className="mono text-[11px] uppercase tracking-wider text-brand">Reviewer Console</span>} description="Every verification case in the system." />
      <CaseQueue title="All Cases" />
    </div>
  )
}
