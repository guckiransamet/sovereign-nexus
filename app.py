import streamlit as st
import json
import os
import random
import base64
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

# ==========================================
# 1. VERİ SİSTEMİ VE ALTYAPI
# ==========================================
DB_PATH = "Portfoy_Gercek_Sistem.json"

def veriyi_yukle():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "projeler" not in data: data = {"projeler": {}}
                return data
        except:
            return {"projeler": {}}
    return {"projeler": {}}

def veriyi_kaydet(sistem):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(sistem, f, ensure_ascii=False, indent=4)

# Uygulama hafızasını başlat
if 'sistem' not in st.session_state:
    st.session_state.sistem = veriyi_yukle()
if 'login_status' not in st.session_state:
    st.session_state.login_status = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None

# ==========================================
# 2. HESAPLAMA MOTORLARI (Birebir Aynı)
# ==========================================
def takvim_hesapla(yil, ay, taksit_sayisi, pesinat1, taksit_eski, taksit_yeni, pesinat2_ay, pesinat2_tutar):
    basla = datetime(yil, ay, 1)
    basla_yili = basla.year
    plan, etiketler = {}, {}
    taksit_no = 1
    toplam_ay = taksit_sayisi + 1
    if pesinat2_ay > 0 and pesinat2_tutar > 0: toplam_ay += 1
    for i in range(toplam_ay):
        ay_tarih = basla + relativedelta(months=i)
        ay_isim = ay_tarih.strftime("%Y-%m")
        if i == 0: tutar, isim = float(pesinat1), "1. Peşinat"
        elif i == pesinat2_ay and float(pesinat2_tutar) > 0: tutar, isim = float(pesinat2_tutar), "2. Peşinat"
        else:
            tutar = float(taksit_yeni) if ay_tarih.year > basla_yili else float(taksit_eski)
            isim = f"Taksit {taksit_no}"; taksit_no += 1
        plan[ay_isim], etiketler[ay_isim] = tutar, isim
    return plan, etiketler

def makbuz_olustur_html(p_ad, o_ad):
    p = st.session_state.sistem["projeler"].get(p_ad, {})
    ortak = next((o for o in p.get("ortaklar", []) if o.get("ad") == o_ad), None)
    if not ortak: return ""
    toplam_maliyet = float(p.get("toplam_maliyet", 0))
    toplam_pay = float(p.get("toplam_pay", 1))
    hisse_borcu = (toplam_maliyet / toplam_pay) * float(ortak.get("pay", 0))
    odenmis = sum(float(tut) for ay, tut in ortak.get("plan", {}).items() if ortak.get("odemeler", {}).get(ay, False))
    kalan = hisse_borcu - odenmis
    return f"""
    <div style="border: 2px solid #cbd5e1; padding: 20px; border-radius: 8px; background-color: #f8fafc; max-width: 450px; margin: auto;">
        <h4 style="text-align: center;">📄 BİLGİLENDİRME MAKBUZU</h4>
        <hr>
        <p><b>Ortak:</b> {o_ad}<br><b>Proje:</b> {p_ad}<br><b>Pay:</b> {ortak.get('pay',0)}</p>
        <div style="background:#e2e8f0; padding:10px; border-radius:5px;">
            <p>Toplam Borç: {hisse_borcu:,.0f} TL<br>Ödenen: {odenmis:,.0f} TL</p>
        </div>
        <div style="text-align:center; padding:10px; background:#fef2f2; margin-top:10px;">
            <b style="color:#dc2626; font-size:20px;">KALAN: {kalan:,.0f} TL</b>
        </div>
    </div>
    """

# ==========================================
# 3. WEB ARAYÜZÜ (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Portföy Yönetim Portalı", layout="wide")

if not st.session_state.login_status:
    # --- GİRİŞ EKRANI ---
    st.markdown("<h2 style='text-align:center;'>🔐 Portföy Giriş Portalı</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tc_input = st.text_input("TC Kimlik Numarası / Admin")
        sifre_input = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP", use_container_width=True):
            if tc_input == "admin" and sifre_input == "admin":
                st.session_state.login_status = True
                st.session_state.user_type = "admin"
                st.rerun()
            else:
                for p_ad, p_data in st.session_state.sistem["projeler"].items():
                    for o in p_data.get("ortaklar", []):
                        if o.get("tc") == tc_input and o.get("sifre") == sifre_input:
                            st.session_state.login_status = True
                            st.session_state.user_type = "ortak"
                            st.session_state.current_user = o
                            st.session_state.current_proje = p_ad
                            st.rerun()
                st.error("Hatalı Giriş Bilgileri!")
else:
    # --- PANEL ÜST KISIM ---
    st.sidebar.title("Menü")
    if st.sidebar.button("🚪 Güvenli Çıkış"):
        st.session_state.login_status = False
        st.rerun()

    if st.session_state.user_type == "admin":
        st.title("👑 Yönetici Paneli")
        t1, t2, t3, t4, t5, t6 = st.tabs(["⚙️ Ayarlar", "✍️ Veri Girişi", "📈 Dashboard", "👥 Ortaklar", "📋 Kasa", "📖 Karar Defteri"])

        with t1:
            st.subheader("Yeni Proje Kur")
            v_ad = st.text_input("Proje Adı")
            v_borc = st.number_input("Toplam Maliyet", value=0.0)
            v_pay = st.number_input("Toplam Pay", value=100)
            if st.button("PROJEYİ KUR"):
                plan, etiketler = takvim_hesapla(2026, 5, 19, 0, 0, 0, 0, 0)
                st.session_state.sistem["projeler"][v_ad] = {
                    "ad": v_ad, "toplam_maliyet": v_borc, "toplam_pay": v_pay,
                    "plan": plan, "etiketler": etiketler, "ortaklar": [], "kasadan_cikan": 0.0, "kasa_log": [], "kararlar": []
                }
                veriyi_kaydet(st.session_state.sistem)
                st.success("Proje Kuruldu!")

        with t2:
            st.subheader("Ortak Ekle")
            p_sec = st.selectbox("Proje Seç", list(st.session_state.sistem["projeler"].keys()))
            if p_sec:
                o_ad = st.text_input("Ad Soyad")
                o_tc = st.text_input("TC")
                o_pay = st.number_input("Pay", value=1)
                if st.button("KAYDET"):
                    st.session_state.sistem["projeler"][p_sec]["ortaklar"].append({
                        "ad": o_ad, "tc": o_tc, "sifre": "123456", "pay": o_pay,
                        "plan": st.session_state.sistem["projeler"][p_sec]["plan"].copy(),
                        "odemeler": {}
                    })
                    veriyi_kaydet(st.session_state.sistem)
                    st.success("Ortak Eklendi")

        with t6:
            st.subheader("📖 Karar Defteri")
            p_k_sec = st.selectbox("Karar Projesi", list(st.session_state.sistem["projeler"].keys()), key="karar_p")
            if p_k_sec:
                k_no = st.text_input("Karar No")
                k_gundem = st.text_area("Gündem")
                k_metin = st.text_area("Karar Metni")
                if st.button("KARARI DEFTERE İŞLE"):
                    st.session_state.sistem["projeler"][p_k_sec].setdefault("kararlar", []).append({
                        "tarih": datetime.now().strftime("%d-%m-%Y"),
                        "no": k_no, "gundem": k_gundem, "metin": k_metin
                    })
                    veriyi_kaydet(st.session_state.sistem)
                    st.success("Karar Kaydedildi.")

    else:
        # --- ORTAK PANELİ ---
        o = st.session_state.current_user
        p_ad = st.session_state.current_proje
        st.title(f"Hoşgeldiniz, {o['ad']}")
        st.markdown(makbuz_olustur_html(p_ad, o['ad']), unsafe_allow_html=True)
        
        st.subheader("🗓️ Ödeme Takviminiz")
        st.write(o["plan"])