import os, io, json, time, textwrap, re, datetime, urllib.parse
import streamlit as st

# ================= 기본 =================
st.set_page_config(page_title="자기소개서 코치", page_icon="💬", layout="wide")
st.markdown("<style>.main .block-container{max-width:480px}</style>", unsafe_allow_html=True)

# ================= 테마 =================
THEME = {
    "PRIMARY":"#0AA6A6","PRIMARY_DARK":"#087F7F",
    "ACCENT":"#00C2C2","SURFACE":"#F5FBFB",
    "TEXT_DARK":"#0F172A","RADIUS":"18px",
    "GRAD_L":"#0FBDBD","GRAD_R":"#099494"
}
try:
    with open("assets/theme.json","r",encoding="utf-8") as f:
        THEME.update(json.load(f))
except Exception:
    pass

# (옵션) 외부 CSS 로드 — 없어도 됨
if os.path.exists("assets/figma.css"):
    with open("assets/figma.css","r",encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 핵심 스타일(헤더/말풍선) + 테마 토큰
st.markdown(f"""
<style>
:root {{
  --primary:{THEME["PRIMARY"]}; --accent:{THEME["ACCENT"]};
  --surface:{THEME["SURFACE"]}; --radius:{THEME["RADIUS"]};
  --gradL:{THEME["GRAD_L"]}; --gradR:{THEME["GRAD_R"]};
}}
body,.stApp{{background:var(--surface);}}
.round-header{{margin:12px 0 8px;background:linear-gradient(135deg,var(--gradL),var(--gradR));
  color:#fff;border-radius:18px;padding:14px 18px;box-shadow:0 8px 20px rgba(0,0,0,.08)}}
.round-header__title{{font-weight:900;letter-spacing:.2px}}
.round-header__sub{{opacity:.95;font-size:12px;margin-top:4px}}
.bubble{{max-width:88%;margin:10px 12px}}
.bubble .bubble-text{{padding:10px 14px;border-radius:18px;display:inline-block}}
.bubble .bubble-time{{font-size:11px;color:#64748b;margin-top:4px}}
.bubble.bot .bubble-text{{background:#F3F4F6;border-radius:18px 18px 18px 4px}}
.bubble.me{{text-align:right}}
.bubble.me .bubble-text{{background:#E8FDFC;border-radius:18px 18px 4px 18px}}
</style>
""", unsafe_allow_html=True)

# ================= 상태 =================
if "screen" not in st.session_state: st.session_state.screen = "onboarding"   # onboarding | main
if "tab"    not in st.session_state: st.session_state.tab = "chat"            # chat | settings | storage | detail
if "msgs"   not in st.session_state:
    st.session_state.msgs = [("bot","안녕하세요! 자기소개서 작성을 도와드릴게요. 어떤 회사/직무에 지원하시나요?", None)]
if "settings" not in st.session_state:
    st.session_state.settings = {
        "provider":"demo","model":"gpt-4o-mini",
        "tone":"정중하고 간결한","length":800,"temperature":0.7,
        "openai_key":"","gemini_key":"",
        "save_dir": os.path.expanduser("~/AI_CoverLetter_Storage")
    }

# ================= 유틸 =================
def now_hhmm():
    return datetime.datetime.now().strftime("%p %I:%M").replace("AM","오전").replace("PM","오후")

def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def slugify(name:str)->str:
    return (re.sub(r'[\\/:*?"<>|]',"_",name).strip() or "coverletter")

def header_card(title:str, subtitle:str=""):
    st.markdown(f"""
    <div class="round-header">
      <div class="round-header__title">{title}</div>
      {f'<div class="round-header__sub">{subtitle}</div>' if subtitle else ''}
    </div>""", unsafe_allow_html=True)

# ---- SVG 아이콘 내장/로드 -> data URI ----
DEFAULT_SVG = {
    "chat":     """<svg viewBox="0 0 24 24" fill="#000"><path d="M4 4h16v12H7l-3 3V4z"/></svg>""",
    "settings": """<svg viewBox="0 0 24 24" fill="#000"><path d="M19.4 12.94a7.5 7.5 0 0 0 .05-.94 7.5 7.5 0 0 0-.05-.94l2.11-1.65a.5.5 0 0 0 .12-.64l-2-3.46a.5.5 0 0 0-.6-.22l-2.49 1a7.55 7.55 0 0 0-1.63-.94l-.38-2.65A.5.5 0 0 0 12 0h-4a.5.5 0 0 0-.5.42l-.38 2.65c-.58.23-1.12.53-1.63.94l-2.49-1a.5.5 0 0 0-.6.22l-2 3.46a.5.5 0 0 0 .12.64L3.6 11.06c-.03.31-.05.63-.05.94s.02.63.05.94L1.49 14.6a.5.5 0 0 0-.12.64l2 3.46a.5.5 0 0 0 .6.22l2.49-1c.51.41 1.05.71 1.63.94l.38 2.65A.5.5 0 0 0 8 22h4a.5.5 0 0 0 .5-.42l.38-2.65c.58-.23 1.12-.53 1.63-.94l2.49 1a.5.5 0 0 0 .6-.22l2-3.46a.5.5 0 0 0-.12-.64L19.4 12.94zM10 14a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/></svg>""",
    "storage":  """<svg viewBox="0 0 24 24" fill="#000"><path d="M10 4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6z"/></svg>""",
    "detail":   """<svg viewBox="0 0 24 24" fill="#000"><path d="M5 4h14v2H5V4zm0 7h14v2H5v-2zm0 7h14v2H5v-2z"/></svg>"""
}
def svg_data_uri(path_or_key:str, key:str=None)->str:
    if key is None:  # direct
        raw = path_or_key
    else:
        if os.path.exists(path_or_key):
            raw = open(path_or_key,"r",encoding="utf-8").read()
        else:
            raw = DEFAULT_SVG[key]
    raw = re.sub(r">\s+<","><",raw.strip())
    return f"data:image/svg+xml;utf8,{urllib.parse.quote(raw)}"

# ================= 저장/변환 =================
def ensure_dir(path:str)->tuple[bool,str]:
    try:
        os.makedirs(path, exist_ok=True)
        test = os.path.join(path,".write_test"); open(test,"w").write("ok"); os.remove(test)
        return True,"OK"
    except PermissionError: return False,"권한이 없습니다. 다른 폴더를 선택하세요."
    except Exception as e:  return False,f"오류: {e}"

def to_docx_bytes(text:str)->bytes:
    from docx import Document
    from docx.shared import Pt
    doc = Document()
    s = doc.styles["Normal"]; s.font.name = "Malgun Gothic"; s.font.size = Pt(11)
    for p in text.split("\n\n"): doc.add_paragraph(p)
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

def _find_korean_font()->tuple[str,int] | tuple[None,None]:
    """PDF 한글용 글꼴 찾기: (path, subfontIndex) 반환"""
    candidates = [
        ("assets/fonts/NanumGothic.ttf", None),
        ("/Library/Fonts/NanumGothic.ttf", None),
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0),
        ("/Library/Fonts/AppleGothic.ttf", None),
        ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", None),
    ]
    for path, idx in candidates:
        if os.path.exists(path):
            return path, (idx if idx is not None else 0)
    return None, None

def to_pdf_bytes(text:str)->bytes:
    # ReportLab + 한글 글꼴 등록
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path, sub_idx = _find_korean_font()
    font_name = "KOR"
    if font_path:
        try:
            if font_path.lower().endswith(".ttc"):
                pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=sub_idx or 0))
            else:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception:
            font_path = None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w,h = A4; x,y = 20*mm, h-20*mm
    if font_path:
        c.setFont(font_name, 11)
    else:
        c.setFont("Helvetica", 11)  # 폰트가 없으면 영문만 정상, 안내는 화면에서.

    max_chars = 45  # 단순 문자수 기준 줄바꿈(한글 가변폭 보정용 여유)
    for line in text.split("\n"):
        wrapped_lines = textwrap.wrap(line, max_chars) or [""]
        for ln in wrapped_lines:
            c.drawString(x,y,ln); y -= 14
            if y < 20*mm:
                c.showPage()
                if font_path: c.setFont(font_name, 11)
                else: c.setFont("Helvetica", 11)
                y = h-20*mm
    c.save()
    return buf.getvalue()

def save_last_result_all(title_base:str, text:str)->list[str]:
    """저장소 폴더에 TXT/DOCX/PDF 저장. 실제 저장된 파일 경로 리스트 반환."""
    s = st.session_state.settings
    ok, msg = ensure_dir(s["save_dir"])
    if not ok:
        st.error(msg); return []
    base = slugify(title_base) + "_" + timestamp()
    paths = []
    # txt
    p_txt = os.path.join(s["save_dir"], base + ".txt")
    with open(p_txt,"w",encoding="utf-8") as f: f.write(text)
    paths.append(p_txt)
    # docx
    p_docx = os.path.join(s["save_dir"], base + ".docx")
    with open(p_docx,"wb") as f: f.write(to_docx_bytes(text))
    paths.append(p_docx)
    # pdf
    p_pdf = os.path.join(s["save_dir"], base + ".pdf")
    pdf_bytes = to_pdf_bytes(text)
    with open(p_pdf,"wb") as f: f.write(pdf_bytes)
    paths.append(p_pdf)
    return paths

# ================= 생성 모델 =================
def call_openai(prompt, sys, model, key, temperature):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key or os.getenv("OPENAI_API_KEY",""))
        r = client.chat.completions.create(
            model=model, temperature=float(temperature),
            messages=[{"role":"system","content":sys},{"role":"user","content":prompt}]
        )
        return r.choices[0].message.content
    except Exception:
        return None

def call_gemini(prompt, sys, model, key, temperature):
    try:
        import google.generativeai as genai
        genai.configure(api_key=key or os.getenv("GEMINI_API_KEY",""))
        m = genai.GenerativeModel(model_name=model, system_instruction=sys)
        r = m.generate_content(prompt, generation_config={"temperature": float(temperature)})
        return getattr(r,"text","").strip() or None
    except Exception:
        return None

def generate_cover_letter(user_text):
    s = st.session_state.settings
    sys = f"너는 인사담당자 출신 자기소개서 코치다. 톤:{s['tone']}, 목표 글자 수:{s['length']}자로 구조화해 작성해라."
    t = s.get("temperature",0.7)
    if s["provider"]=="openai" and (s["openai_key"] or os.getenv("OPENAI_API_KEY")):
        out = call_openai(user_text, sys, s["model"], s["openai_key"], t)
        if out: return out
    if s["provider"]=="gemini" and (s["gemini_key"] or os.getenv("GEMINI_API_KEY")):
        out = call_gemini(user_text, sys, s["model"], s["gemini_key"], t)
        if out: return out
    return ("[DEMO]\n\n1) 지원 동기\n2) 핵심 역량/사례\n3) 협업/문제해결 경험\n4) 입사 후 포부\n\n"
            "JD 키워드를 한 줄로 알려주세요. (예: 데이터 분석, SQL, 대시보드)")

# ================= 입력/탭 UI (하단 고정) =================
def bottom_tabs(active="chat"):
    # data URI (내장 → 파일 우선)
    chat_uri     = svg_data_uri("assets/icons/chat.svg","chat")
    settings_uri = svg_data_uri("assets/icons/settings.svg","settings")
    storage_uri  = svg_data_uri("assets/icons/storage.svg","storage")
    detail_uri   = svg_data_uri("assets/icons/detail.svg","detail")

    tabs   = ["chat", "settings", "storage", "detail"]
    labels = {"chat":"대화","settings":"설정","storage":"저장소","detail":"세부설정"}
    active_idx = tabs.index(active) + 1

    st.markdown('<div id="bottom-nav">', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    if c1.button(labels["chat"], use_container_width=True):       st.session_state.tab = "chat"
    if c2.button(labels["settings"], use_container_width=True):   st.session_state.tab = "settings"
    if c3.button(labels["storage"], use_container_width=True):    st.session_state.tab = "storage"
    if c4.button(labels["detail"], use_container_width=True):     st.session_state.tab = "detail"
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <style>
      #bottom-nav {{
        position: fixed; left:0; right:0; bottom:0;
        padding: 8px 24px 10px; z-index: 40;
        background: transparent;
      }}
      /* 입력창: 탭 위로 띄우고 캡슐/그림자 */
      div[data-testid="stChatInput"] {{
        position: fixed !important; left: 16px; right: 16px; bottom: 76px !important;
      }}
      div[data-testid="stChatInput"] label {{ display:none !important; }}
      div[data-testid="stChatInput"] textarea {{
        border-radius: 999px !important;
        border: 1px solid #E3E8EF !important;
        background: #fff !important;
        box-shadow: 0 6px 20px rgba(16,24,40,.08) !important;
        padding: 12px 16px !important;
      }}
      .main .block-container {{ padding-bottom: 280px !important; }}

      #bottom-nav .stButton > button {{
        background: transparent !important; border:0 !important;
        box-shadow:none !important; border-radius:0 !important;
        height:auto !important; padding:6px 0 4px !important;
        color:#64748B !important; font-weight:700;
        display:inline-flex; flex-direction:column; align-items:center; gap:4px;
      }}
      /* 아이콘 마스크 */
      #bottom-nav .stButton > button::before {{
        content:""; width:24px; height:24px; display:block; margin:0 auto 4px;
        background-color:#64748B; -webkit-mask-repeat:no-repeat; mask-repeat:no-repeat;
        -webkit-mask-position:center; mask-position:center;
        -webkit-mask-size:24px 24px; mask-size:24px 24px;
      }}
      #bottom-nav .stButton:nth-of-type(1) > button::before {{ -webkit-mask-image:url('{chat_uri}');    mask-image:url('{chat_uri}');    }}
      #bottom-nav .stButton:nth-of-type(2) > button::before {{ -webkit-mask-image:url('{settings_uri}');mask-image:url('{settings_uri}');}}
      #bottom-nav .stButton:nth-of-type(3) > button::before {{ -webkit-mask-image:url('{storage_uri}'); mask-image:url('{storage_uri}'); }}
      #bottom-nav .stButton:nth-of-type(4) > button::before {{ -webkit-mask-image:url('{detail_uri}');  mask-image:url('{detail_uri}');  }}

      #bottom-nav .stButton:nth-of-type({active_idx}) > button {{
        color: var(--primary) !important;
      }}
      #bottom-nav .stButton:nth-of-type({active_idx}) > button::before {{
        background-color: var(--primary) !important;
      }}
    </style>
    """, unsafe_allow_html=True)

# ================= 명령 인식(저장) =================
SAVE_PATTERNS = [
    r"/save", r"저장해줘", r"저장해", r"저장하기", r"저장소에\s*저장", r"자기소개서.*저장", r"생성된\s*자기소개서.*저장"
]
SAVE_REGEX = re.compile("|".join(SAVE_PATTERNS))

def is_save_command(txt:str)->bool:
    return bool(SAVE_REGEX.search(txt.replace(" ", "")))

def handle_save_command():
    # 마지막 bot 응답 찾기
    last_bot = None
    for role, text, ts in reversed(st.session_state.msgs):
        if role == "bot":
            last_bot = text; break
    if not last_bot:
        st.session_state.msgs.append(("bot","저장할 자기소개서가 아직 없습니다. 먼저 ‘대화’에서 초안을 생성해 주세요.", now_hhmm()))
        return
    paths = save_last_result_all("자기소개서", last_bot)
    if not paths:  # 권한 실패 등
        return
    msg = "저장 완료!\n\n" + "\n".join(f"- {p}" for p in paths)
    # 폰트가 없으면 PDF는 영문만 정상일 수 있음 → 안내
    font_path, _ = _find_korean_font()
    if not font_path:
        msg += "\n\n※ PDF 한글용 글꼴이 없어서 한글이 깨질 수 있습니다.\n" \
               "assets/fonts/NanumGothic.ttf 를 추가하면 깨지지 않습니다."
    st.session_state.msgs.append(("bot", msg, now_hhmm()))

# ================= 화면들 =================
def screen_onboarding():
    header_card("자기소개서 코치", "대화로 초안 만들기")
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:center;height:64vh">
      <div style="width:88%;max-width:520px;background:#F5FBFB;border-radius:24px;box-shadow:0 10px 30px rgba(0,0,0,.08);padding:28px;text-align:center">
        <div style="font-size:56px;margin-bottom:12px">🤖</div>
        <div style="font-weight:800;font-size:22px;margin:6px 0 8px">AI 자기소개서 작성</div>
        <div style="color:#475569;line-height:1.6">
          AI가 도와주는 맞춤형 자기소개서를 작성해보세요.<br/>
          간단한 대화를 통해 전문적인 자기소개서를 완성할 수 있습니다.
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("시작하기", use_container_width=True):
        st.session_state.screen = "main"; st.session_state.tab = "chat"

def screen_chat():
    header_card("자기소개서 코치", "대화로 초안 만들기")

    for role, text, ts in st.session_state.msgs:
        ts = ts or now_hhmm()
        if role=="bot":
            st.markdown(f"""
            <div class="bubble bot"><div class="bubble-text">{text}</div>
            <div class="bubble-time">{ts}</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="bubble me"><div class="bubble-text">{text}</div>
            <div class="bubble-time">{ts}</div></div>""", unsafe_allow_html=True)

    user = st.chat_input("메시지를 입력하세요...")
    if user:
        # 1) 저장 명령이면 저장만 수행하고 종료
        if is_save_command(user):
            handle_save_command()
        else:
            st.session_state.msgs.append(("user", user, now_hhmm()))
            with st.spinner("생성 중…"):
                reply = generate_cover_letter(user); time.sleep(0.2)
            st.session_state.msgs.append(("bot", reply, now_hhmm()))

    # 입력창 아래 고정 탭
    bottom_tabs("chat")

def screen_settings():
    header_card("환경 설정", "모델·길이·창의성 조절")
    s = st.session_state.settings
    s["provider"] = {"demo(키 없음)":"demo","openai":"openai","gemini":"gemini"}[
        st.selectbox("엔진 제공자", ["demo(키 없음)","openai","gemini"],
                     index={"demo":0,"openai":1,"gemini":2}.get(s["provider"],0))
    ]
    if s["provider"]=="openai":
        s["openai_key"] = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        s["model"] = st.selectbox("OpenAI 모델", ["gpt-4o-mini","gpt-4o"], index=0)
    elif s["provider"]=="gemini":
        s["gemini_key"] = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
        s["model"] = st.selectbox("Gemini 모델", ["gemini-1.5-pro","gemini-1.5-flash"], index=1)
    else:
        st.caption("데모 모드: 실제 호출 없이 예시 응답입니다.")
    s["tone"] = st.selectbox("톤(어조)", ["정중하고 간결한","따뜻하고 진정성 있는","논리적이고 직설적인"],
                             index=["정중하고 간결한","따뜻하고 진정성 있는","논리적이고 직설적인"].index(s["tone"]))
    s["length"] = st.slider("목표 글자 수", 300, 1500, s["length"], 50)
    s["temperature"] = st.slider("창의성(temperature)", 0.0, 1.0, s.get("temperature",0.7), 0.05)

    bottom_tabs("settings")

def screen_storage():
    header_card("저장소", "내 PC에서 파일 내려받기")
    path = st.session_state.settings["save_dir"]
    ok, msg = ensure_dir(path)
    if not ok:
        st.error(msg)
    else:
        st.caption(f"저장 경로: {path}")
        files = sorted([f for f in os.listdir(path) if f.endswith((".txt",".md",".docx",".pdf"))])
        if not files:
            st.info("아직 저장된 파일이 없습니다.")
        else:
            for name in files:
                with open(os.path.join(path,name),"rb") as f:
                    st.download_button(f"다운로드: {name}", data=f.read(), file_name=name, use_container_width=True)
    bottom_tabs("storage")

def screen_detail():
    header_card("세부설정", "생성 결과 저장/내보내기/번역")
    if st.session_state.msgs and st.session_state.msgs[-1][0]=="bot":
        last = st.session_state.msgs[-1][1]
        title = st.text_input("파일 제목", value="자기소개서")
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            if st.button("저장소에 저장", use_container_width=True):
                paths = save_last_result_all(title, last)
                st.success("저장 완료!\n" + "\n".join(paths))
        with c2:
            st.download_button("DOCX", data=to_docx_bytes(last),
                file_name=f"{slugify(title)}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)
        with c3:
            st.download_button("PDF", data=to_pdf_bytes(last),
                file_name=f"{slugify(title)}.pdf", mime="application/pdf",
                use_container_width=True)
        with c4:
            if st.button("영문 변환", use_container_width=True):
                with st.spinner("영문 변환 중…"):
                    en = generate_cover_letter(f"[영문 번역]\n{last}"); time.sleep(0.2)
                st.session_state.msgs.append(("bot", f"**영문 변환본**\n\n{en}", now_hhmm()))
                st.success("대화에 영문 변환본이 추가되었습니다.")
    else:
        st.info("먼저 ‘대화’ 탭에서 내용을 생성해 주세요.")
    bottom_tabs("detail")

# ================= 라우팅 =================
if st.session_state.screen == "onboarding":
    screen_onboarding()
else:
    {"chat":screen_chat, "settings":screen_settings, "storage":screen_storage, "detail":screen_detail}[st.session_state.tab]()
