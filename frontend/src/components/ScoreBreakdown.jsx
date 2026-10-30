// Shows exactly how the score was computed, so users (and examiners) can verify it.
export default function ScoreBreakdown({ score }) {
  return (
    <div className="max-w-2xl">
      <table className="w-full text-sm">
        <tbody>
          <tr className="text-muted">
            <td className="py-2">Starting score</td>
            <td />
            <td className="py-2 text-right font-semibold tabular-nums text-ink">100</td>
          </tr>
          {score.components.map((c) => (
            <tr key={c.key} className="border-t border-line">
              <td className="py-2 pr-3 font-medium">{c.label}</td>
              <td className="py-2 pr-3 text-muted">{c.detail}</td>
              <td className={`py-2 text-right font-semibold tabular-nums ${c.points < 0 ? 'text-bad-ink' : c.points > 0 ? 'text-good-ink' : 'text-muted'}`}>
                {c.points > 0 ? '+' : ''}{c.points}
              </td>
            </tr>
          ))}
          <tr className="border-t-2 border-ink/80">
            <td className="py-2.5 font-bold">Final score</td>
            <td className="py-2.5 text-xs text-muted">clamped to 0-100, rounded</td>
            <td className="py-2.5 text-right text-lg font-extrabold tabular-nums">{score.score}</td>
          </tr>
        </tbody>
      </table>
      {score.missing.length > 0 && (
        <p className="mt-3 text-xs text-muted">Not on the label (counted as 0): {score.missing.join(', ').replace(/_/g, ' ')}</p>
      )}
      <p className="mt-2 text-xs text-muted">Plain Python formula, no AI: the same label always gets the same score. Full formula on the About page.</p>
    </div>
  )
}
