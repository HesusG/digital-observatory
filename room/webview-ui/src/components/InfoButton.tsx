import { useState } from 'react';

import { Modal } from './ui/Modal.js';

// Small "ℹ️" button (bottom-left of the office) that explains the project.
export function InfoButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="absolute bottom-10 left-10 z-30 pixel-panel w-14 h-14 flex items-center justify-center text-2xl cursor-pointer hover:text-accent-bright"
        title="¿Qué es esto?"
      >
        ℹ️
      </button>

      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title={<span className="text-2xl">🏢 Mi oficina de marketing</span>}
        zIndex={60}
      >
        <div className="py-4 px-10 max-h-[60vh] overflow-y-auto text-sm leading-relaxed flex flex-col gap-8">
          <p>
            Una oficina de <b>agentes de IA</b> que convierte artículos de IA/EdTech en posts para
            redes sociales, para promover un curso «AI for Teachers». Cada personaje es un agente:
          </p>

          <ul className="m-0 pl-16 list-disc flex flex-col gap-3">
            <li>
              <b>🔭 Tess</b> — puntúa qué tan relevante es cada artículo para docentes.
            </li>
            <li>
              <b>✍️ Carla</b> — redacta el post por plataforma e idioma.
            </li>
            <li>
              <b>📐 Edu</b> — revisa voz, datos y reglas de cada red; aprueba o pide cambios.
            </li>
            <li>
              <b>📤 Pablo</b> — publica en Bluesky (vía Postiz) cuando tú apruebas.
            </li>
          </ul>

          <div>
            <div className="text-accent-bright mb-3">Stack</div>
            <ul className="m-0 pl-16 list-disc flex flex-col gap-2">
              <li>Python + FastAPI — el orquestador «observatory».</li>
              <li>ChromaDB (memoria) · Ollama gemma3 en el Ryzen (los cerebros, vía Wake-on-LAN).</li>
              <li>Postiz + Bluesky — la publicación.</li>
              <li>
                Este cuarto: React + Canvas (fork de pixel-agents), alimentado por un event-log vía
                SSE (<code>/api/events</code>).
              </li>
            </ul>
          </div>
        </div>
      </Modal>
    </>
  );
}
