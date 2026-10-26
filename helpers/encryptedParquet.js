/**
 * encryptedParquet.js — open a KEP1 container (AES-256-GCM over parquet bytes) in the browser
 * and hand it to Observable's DuckDBClient as if it were a FileAttachment.
 *
 * Producer: data/KE-enso-explorer/_sources/kamis_build.py (see its OBFUSCATED DELIVERY note).
 * Container: b"KEP1" | mode (0x00 raw key, 0x01 PBKDF2 password) | salt(16) | iv(12) | ciphertext+tag
 * AAD = the 4-byte magic.
 *
 * THIS IS OBFUSCATION, NOT ACCESS CONTROL. A static page must hold whatever decrypts, so anyone
 * with devtools can recover the bytes. Agreed 2026-10-23 as a courtesy to MoALD (KAMIS) while reuse
 * terms are sought: it stops casual download and crawlers, nothing more. Say so to partners.
 *
 * DuckDB-WASM cannot read DuckDB's own parquet encryption (verified 2026-10-23, it aborts in the
 * decryptor), hence WebCrypto here and plain bytes registered with the client.
 *
 * Usage in an {ojs} cell (notebook owner wires this; this module does not touch the notebook):
 *
 *   encParquet = import("/helpers/encryptedParquet.js")
 *   kamisSrc = encParquet.decryptedAttachment(
 *     FileAttachment("/data/KE-enso-explorer/market_prices_kamis.parquet.enc"),
 *     { keyHex: "<64 hex chars>" }            // raw-key container (mode 0)
 *     // or { password: "<reviewer password>" }  // PBKDF2 container (mode 1): nothing secret in the page
 *   )
 *   dbPrices = DuckDBClient.of({
 *     market_prices: FileAttachment("/data/KE-enso-explorer/market_prices.parquet"),
 *     market_prices_kamis: kamisSrc,
 *   })
 *
 * The returned object mimics the FileAttachment surface DuckDBClient reads: `name` (ends in
 * .parquet so the client issues parquet_scan), `url()` returning a blob: URL (so it registers the
 * buffer rather than a remote URL), `arrayBuffer()` and `mimeType`.
 */

const MAGIC = new Uint8Array([0x4b, 0x45, 0x50, 0x31]); // "KEP1"
const PBKDF2_ROUNDS = 200000;

function hexToBytes(hex) {
  const clean = String(hex).trim();
  if (!/^[0-9a-fA-F]{64}$/.test(clean)) throw new Error("keyHex must be 64 hex characters (32 bytes)");
  return Uint8Array.from(clean.match(/../g), (h) => parseInt(h, 16));
}

async function keyFromHex(hex) {
  return crypto.subtle.importKey("raw", hexToBytes(hex), "AES-GCM", false, ["decrypt"]);
}

async function keyFromPassword(password, salt) {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations: PBKDF2_ROUNDS },
    base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]
  );
}

/** Decrypt a KEP1 container. `opts.keyHex` for mode 0, `opts.password` for mode 1. Returns Uint8Array. */
export async function decryptContainer(bytes, opts = {}) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (b.length < 33 || b[0] !== MAGIC[0] || b[1] !== MAGIC[1] || b[2] !== MAGIC[2] || b[3] !== MAGIC[3]) {
    throw new Error("not a KEP1 container");
  }
  const mode = b[4];
  const salt = b.slice(5, 21);
  const iv = b.slice(21, 33);
  const ct = b.slice(33);
  let key;
  if (mode === 1) {
    if (!opts.password) throw new Error("container is password-derived; pass { password }");
    key = await keyFromPassword(opts.password, salt);
  } else if (mode === 0) {
    if (!opts.keyHex) throw new Error("container uses a raw key; pass { keyHex }");
    key = await keyFromHex(opts.keyHex);
  } else {
    throw new Error(`unknown KEP1 mode ${mode}`);
  }
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv, additionalData: MAGIC }, key, ct);
  return new Uint8Array(plain);
}

/**
 * Fetch + decrypt an encrypted attachment and return a FileAttachment-like object for
 * DuckDBClient.of(). `name` defaults to the attachment name without its trailing ".enc".
 */
export async function decryptedAttachment(attachment, opts = {}) {
  const raw = await attachment.arrayBuffer();
  const plain = await decryptContainer(raw, opts);
  const name = opts.name || String(attachment.name || "encrypted.parquet").replace(/\.enc$/i, "");
  if (!/\.parquet$/i.test(name)) throw new Error("decrypted attachment name must end in .parquet");
  const blob = new Blob([plain], { type: "application/vnd.apache.parquet" });
  const blobUrl = URL.createObjectURL(blob);
  return {
    name,
    mimeType: "application/vnd.apache.parquet",
    url: async () => blobUrl,
    arrayBuffer: async () => plain.buffer.slice(plain.byteOffset, plain.byteOffset + plain.byteLength),
    bytes: plain,
  };
}
