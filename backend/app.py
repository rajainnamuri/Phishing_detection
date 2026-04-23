import streamlit as st

# =========================================================
# MUST BE FIRST STREAMLIT COMMAND
# =========================================================
st.set_page_config(page_title="Website Checker Bot", layout="centered")

# =========================================================
# IMPORTS
# =========================================================
import requests
import re
import numpy as np
import ipaddress
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from tensorflow.keras.models import load_model

# =========================================================
# CONFIG
# =========================================================
ERROR_KEYWORDS = [
    "404 not found",
    "this site can’t be reached",
    "can't reach this page",
    "url not found",
    "page not found",
    "site can’t be reached"
]

SIMILARITY_HIGH = 0.7
SIMILARITY_MED = 0.5
HIGH_RISK_SCORE = 70

# =========================================================
# LOAD MODELS
# =========================================================
@st.cache_resource
def load_bert():
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource
def load_url_model():
    return load_model("url_model.h5")

bert_model = load_bert()
url_model = load_url_model()

# =========================================================
# URL FEATURE HELPERS
# =========================================================
def fd_length(url):
    path = urlparse(url).path
    try:
        return len(path.split('/')[1])
    except:
        return 0

def digit_count(url):
    return sum(c.isdigit() for c in url)

def letter_count(url):
    return sum(c.isalpha() for c in url)

def no_of_dir(url):
    return urlparse(url).path.count('/')

def having_ip_address(url):
    try:
        ipaddress.ip_address(urlparse(url).netloc)
        return 1
    except:
        return 0

# =========================================================
# URL FEATURE EXTRACTION (16 FEATURES)
# =========================================================
def extract_url_features(url):
    parsed = urlparse(url)

    features = [
        len(parsed.netloc),           # hostname_length
        len(parsed.path),             # path_length
        fd_length(url),               # fd_length
        url.count('-'),               # count-
        url.count('@'),               # count@
        url.count('?'),               # count?
        url.count('%'),               # count%
        url.count('.'),               # count.
        url.count('='),               # count=
        url.count('http'),            # count-http
        url.count('https'),           # count-https
        url.count('www'),             # count-www
        digit_count(url),             # count-digits
        letter_count(url),            # count-letters
        no_of_dir(url),               # count_dir
        having_ip_address(url)        # use_of_ip
    ]

    return np.array(features, dtype=np.float32).reshape(1, -1)

# =========================================================
# URL STRUCTURE ANALYSIS
# =========================================================
def url_abnormality_check(url):
    try:
        features = extract_url_features(url)
        prediction = url_model.predict(features, verbose=0)

        # Robust output handling
        if prediction.ndim == 2:
            if prediction.shape[1] == 1:
                score = prediction[0][0]        # sigmoid
            else:
                score = prediction[0][1]        # softmax
        else:
            score = prediction[0]

        if score > 0.5:
            return "🚨 Abnormalities Found", True
        else:
            return "✅ No Abnormalities Found", False

    except Exception as e:
        return f"⚠️ URL structure analysis failed ({str(e)})", None

# =========================================================
# WEBSITE STATUS CHECK
# =========================================================
def check_website_status(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)

        page_text = response.text.lower()

        if response.status_code in [404, 500, 502, 503, 504]:
            return False, "Website returned server error"

        for word in ERROR_KEYWORDS:
            if word in page_text:
                return False, "Website unreachable or error page"

        return True, response.text

    except Exception:
        return False, "Website cannot be reached"

# =========================================================
# TEXT EXTRACTION
# =========================================================
def extract_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()

# =========================================================
# LOAD CUSTOM RULES
# =========================================================
def load_custom_sentences(path="custom_sentences.txt"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

# =========================================================
# BERT CONTENT ANALYSIS
# =========================================================
def bert_similarity(web_text, custom_sentences):

    if not custom_sentences:
        return [], 0, "NO_RULES"

    words = web_text.split()
    if len(words) < 50:
        return [], HIGH_RISK_SCORE, "NO_TEXT"

    trimmed_text = " ".join(words[:100])

    web_embedding = bert_model.encode([trimmed_text], show_progress_bar=False)
    rule_embeddings = bert_model.encode(custom_sentences, show_progress_bar=False)

    sims = cosine_similarity(web_embedding, rule_embeddings)[0]

    matches = []
    score = 0

    for i, sim in enumerate(sims):
        if sim >= SIMILARITY_HIGH:
            matches.append((custom_sentences[i], sim))
            score += 40
        elif sim >= SIMILARITY_MED:
            matches.append((custom_sentences[i], sim))
            score += 25

    if len(matches) > 1:
        score += 20

    return matches, score, "TEXT_ANALYZED"

# =========================================================
# STREAMLIT UI
# =========================================================
st.title("🌐 Website Checker Bot")
st.caption("Hybrid analysis using **URL Structure + BERT Content Analysis**")

url = st.text_input("Enter Website URL")

if st.button("Check Website"):

    if not url:
        st.warning("Please enter a URL")
        st.stop()

    with st.spinner("Analyzing..."):

        # ---------- URL STRUCTURE ----------
        structure_result, is_abnormal = url_abnormality_check(url)
        url_safe = not is_abnormal

        st.subheader("🔗 URL Structure Analysis")
        st.write(structure_result)

        # ---------- WEBSITE STATUS ----------
        reachable, response = check_website_status(url)
        if not reachable:
            st.error("🚨 Unsafe Website")
            st.write(response)
            st.stop()

        # ---------- CONTENT ANALYSIS ----------
        text = extract_visible_text(response)
        rules = load_custom_sentences()
        matches, score, flag = bert_similarity(text, rules)

        if score >= 61:
            content_status = "🚨 Unsafe"
            content_safe = False
        elif score >= 31:
            content_status = "⚠️ Moderately Safe"
            content_safe = False
        else:
            content_status = "✅ Safe"
            content_safe = True

        st.subheader("📄 Content Analysis")
        st.write("**Status:**", content_status)
        st.write("**Risk Score:**", score)

        if flag == "NO_TEXT":
            st.warning("Script-heavy or protected content")
        elif matches:
            st.subheader("⚠️ Matched Content")
            for t, s in matches:
                st.write(f"- `{t}` (Similarity: {s:.2f})")
        else:
            st.success("No risky content detected")

        # ---------- FINAL VERDICT ----------
        st.subheader("🧠 Final Verdict")

        if not url_safe and not content_safe:
            st.error("🚨 Unsafe Website")
        elif url_safe and content_safe:
            st.success("✅ Safe Website")
        else:
            st.warning("⚠️ Moderately Safe Website")
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread

# =========================================================
# FLASK APP FOR EXTENSION
# =========================================================
flask_app = Flask(__name__)
CORS(flask_app)

@flask_app.route("/api/check", methods=["POST"])
def check_api():
    data = request.get_json()
    url = data.get("url", "")

    # ---------- URL STRUCTURE ANALYSIS ----------
    structure_result, is_abnormal = url_abnormality_check(url)
    url_safe = not is_abnormal

    # ---------- WEBSITE REACHABILITY ----------
    reachable, response = check_website_status(url)

    if not reachable:
        return jsonify({
            "url_structure": structure_result,
            "content_status": "🚨 Unsafe",
            "risk_score": 80,
            "final_verdict": "🚨 Unsafe Website"
        })

    # ---------- CONTENT ANALYSIS ----------
    text = extract_visible_text(response)
    rules = load_custom_sentences()
    matches, score, flag = bert_similarity(text, rules)

    if score >= 61:
        content_status = "🚨 Unsafe"
        content_safe = False
    elif score >= 31:
        content_status = "⚠️ Moderately Safe"
        content_safe = False
    else:
        content_status = "✅ Safe"
        content_safe = True

    # ---------- FINAL VERDICT (YOUR RULE) ----------
    if not url_safe and not content_safe:
        final_verdict = "🚨 Unsafe Website"
    elif url_safe and content_safe:
        final_verdict = "✅ Safe Website"
    else:
        final_verdict = "⚠️ Moderately Safe Website"

    return jsonify({
        "url_structure": structure_result,
        "content_status": content_status,
        "risk_score": score,
        "final_verdict": final_verdict
    })


def run_flask():
    flask_app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

# Run Flask in background (so Streamlit still works)
Thread(target=run_flask, daemon=True).start()

