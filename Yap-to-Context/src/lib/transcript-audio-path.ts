import path from "path";
import { getAudioStoragePath } from "@/lib/env";

/**
 * Resolve a transcript's stored `audio_relpath` to an absolute path only when
 * it lies under the configured audio storage directory (prevents path escape).
 */
export function resolveTranscriptAudioAbs(relpath: string): string | null {
  const trimmed = relpath.trim();
  if (!trimmed) return null;

  const audioRoot = path.resolve(getAudioStoragePath());
  const resolved = path.isAbsolute(trimmed)
    ? path.resolve(trimmed)
    : path.resolve(process.cwd(), trimmed);

  const normRoot = path.normalize(audioRoot);
  const normFile = path.normalize(resolved);
  const prefix = normRoot.endsWith(path.sep) ? normRoot : `${normRoot}${path.sep}`;

  if (normFile === normRoot || normFile.startsWith(prefix)) {
    return normFile;
  }
  return null;
}
