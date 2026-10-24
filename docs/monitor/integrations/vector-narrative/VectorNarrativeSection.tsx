// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Integration: OpenAI Codex.
import styles from "./vector-narrative.module.css";

const application = "https://pacman-kausale-reise.ingolf-lohmann.chatgpt.site/";
const assets = "/vector-narratives/ein-punkt-zwei-welten";

export function VectorNarrativeSection({ id = "vektorerzaehlung" }: { id?: string }) {
  return (
    <section id={id} className={styles.section} aria-labelledby={`${id}-title`}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Vektorerzählungen / 01 · QIK-VRT</p>
          <h2 id={`${id}-title`} className={styles.title}>Ein Punkt. Zwei Welten.</h2>
        </div>
        <a className={styles.open} href={application} target="_blank" rel="noopener noreferrer"
          aria-label="Ein Punkt. Zwei Welten. – Anwendung in einem neuen Tab öffnen">
          Anwendung öffnen <span aria-hidden="true">↗</span>
        </a>
      </div>
      <p className={styles.description}>
        Eine spielerische Bildmetapher zu Kausalität, Verbindung und Unschärfe.
        {" "}Idee &amp; Dramaturgie: Ingolf Lohmann · Gestaltung &amp; Animation: KI-unterstützt.
      </p>
      <div className={styles.downloads}>
        <a className={styles.download} href={`${assets}/Ein_Punkt_Zwei_Welten.mp4`}
          download="Ein_Punkt_Zwei_Welten.mp4" type="video/mp4">
          <span aria-hidden="true">↓</span> Video speichern (.mp4)
        </a>
        <a className={styles.download} href={`${assets}/Ein_Punkt_Zwei_Welten_Vektorpaket.zip`}
          download="Ein_Punkt_Zwei_Welten_Vektorpaket.zip" type="application/zip">
          <span aria-hidden="true">↓</span> SVG/HTML-Paket (.zip)
        </a>
      </div>
      <p className={styles.offline}>
        Für die Offline-Nutzung das ZIP entpacken und die enthaltene HTML-Datei öffnen.
      </p>
    </section>
  );
}
