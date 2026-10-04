module.exports = async function handler(req, res) {
  const source = "https://github.com/saeid1979/rest/releases/download/artgallery-v2.0/ArtGallery-v2.0.apk";
  try {
    const r = await fetch(source, {
      redirect: "follow",
      headers: { "User-Agent": "ArtGallery-Download-Proxy/1.0" }
    });
    if (!r.ok) {
      res.status(r.status).send("Download source returned " + r.status);
      return;
    }
    const buf = Buffer.from(await r.arrayBuffer());
    res.setHeader("Content-Type", "application/vnd.android.package-archive");
    res.setHeader("Content-Disposition", 'attachment; filename="ArtGallery-v2.0.apk"');
    res.setHeader("Content-Length", String(buf.length));
    res.setHeader("Cache-Control", "public, max-age=3600");
    res.status(200).send(buf);
  } catch (e) {
    res.status(502).send("Download proxy error");
  }
};