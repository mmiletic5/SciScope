type CorpusNoteProps = {
  /** corpus_version from the latest response, when present. */
  corpusVersion?: string | null
}

export function CorpusNote({ corpusVersion }: CorpusNoteProps) {
  return (
    <p className="corpus-note">
      Corpus: 17 open-access honey bee papers (PLOS ONE). Answers are generated from retrieved passages
      and may be wrong; check the cited sources.
      {corpusVersion ? <> Corpus version: <code>{corpusVersion}</code></> : null}
    </p>
  )
}
