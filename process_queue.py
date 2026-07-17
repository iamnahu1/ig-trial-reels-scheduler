import os, json, urllib.request, urllib.error
from datetime import datetime, timezone

KEY = os.environ["COMPOSIO_API_KEY"]
PROXY = "https://backend.composio.dev/api/v3/tools/execute/proxy"

def proxy(conn, method, endpoint, body=None):
    payload = {"connected_account_id": conn, "method": method, "endpoint": endpoint}
    if body is not None:
        payload["body"] = body
    req = urllib.request.Request(PROXY, data=json.dumps(payload).encode(), method="POST")
    req.add_header("x-api-key", KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read().decode())
    return j.get("status"), j.get("data")

def main():
    with open("queue.json") as f:
        q = json.load(f)
    conn = q["connected_account_id"]
    ig = q["ig_user_id"]
    base = "https://graph.instagram.com/v25.0"
    now = datetime.now(timezone.utc)
    did = False
    for e in q.get("entries", []):
        label = e.get("label", "?")
        cid = str(e["creation_id"])
        due = datetime.fromisoformat(e["publish_after_utc"].replace("Z", "+00:00"))
        if now < due:
            print("[%s] todavia no (%s)" % (label, e["publish_after_utc"]))
            continue
        st, data = proxy(conn, "GET", "%s/%s?fields=status_code" % (base, cid))
        status = data.get("status_code") if isinstance(data, dict) else None
        print("[%s] due; container=%s" % (label, status))
        if status == "PUBLISHED":
            print("[%s] ya publicado, skip" % label); continue
        if status != "FINISHED":
            print("[%s] container no FINISHED (%s), skip" % (label, status)); continue
        st2, pub = proxy(conn, "POST", "%s/%s/media_publish" % (base, ig), {"creation_id": cid})
        pid = pub.get("id") if isinstance(pub, dict) else None
        if pid:
            _, perm = proxy(conn, "GET", "%s/%s?fields=permalink" % (base, pid))
            link = perm.get("permalink") if isinstance(perm, dict) else None
            print("[%s] PUBLICADO id=%s %s" % (label, pid, link)); did = True
        else:
            print("[%s] respuesta publish: %s" % (label, pub))
    if not did:
        print("Nada para publicar en este tick.")

if __name__ == "__main__":
    main()
