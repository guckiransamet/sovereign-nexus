import streamlit as st
import json
import os
import random
import base64
import traceback
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

if 'sistem' not in st.session_state:
    st.session_state.sistem = veriyi_yukle()
if 'login_status' not in st.session_state:
    st.session_state.login_status = False

# ==========================================
# 2. TEMEL MOTORLAR (HESAPLAMA VE MAKBUZ)
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

def makbuz_olustur_html(p_ad, o_ad, islem_notu=""):
    p = st.session_state.sistem["projeler"].get(p_ad, {})
    ortak = next((o for o in p.get("ortaklar", []) if o.get("ad") == o_ad), None)
    if not ortak: return ""

    toplam_maliyet = float(p.get("toplam_maliyet", 0))
    toplam_pay = float(p.get("toplam_pay", 1))
    hisse_borcu = (toplam_maliyet / toplam_pay) * float(ortak.get("pay", 0)) if toplam_pay > 0 else 0
    odenmis = sum(float(tut) for ay, tut in ortak.get("plan", {}).items() if ortak.get("odemeler", {}).get(ay, False))
    kalan = hisse_borcu - odenmis

    bugun = date.today()
    gecikenler = []
    for ay, tut in ortak.get("plan", {}).items():
        if not ortak.get("odemeler", {}).get(ay, False):
            try:
                y, a = map(int, ay.split('-')); vade = date(y, a, 15)
                if bugun > vade + timedelta(days=15): gecikenler.append(ay)
            except: pass

    durum_notu = f"<span style='color:#dc2626;'><b>⚠️ {len(gecikenler)} taksit gecikmeniz bulunmaktadır!</b></span>" if gecikenler else "<span style='color:#16a34a;'><b>✅ Ödemeleriniz günceldir.</b></span>"
    islem_html = f"<div style='background:#dcfce7; padding:8px; margin-bottom:15px; color:#166534; text-align:center; border-radius:5px;'><b>✅ {islem_notu}</b></div>" if islem_notu else ""

    return f"""
    <div style="border: 2px solid #cbd5e1; padding: 20px; border-radius: 8px; font-family: sans-serif; background-color: #f8fafc; max-width: 500px; margin: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        {islem_html}
        <h4 style="text-align: center; color: #0f172a; margin-top: 0; border-bottom: 2px dashed #cbd5e1; padding-bottom: 10px;">📄 BİLGİLENDİRME MAKBUZU</h4>
        <table style="width:100%; font-size:14px; margin-bottom:15px;">
            <tr><td>Sayın:</td><td style="text-align:right;"><b>{o_ad}</b></td></tr>
            <tr><td>Proje:</td><td style="text-align:right;"><b>{p_ad}</b></td></tr>
            <tr><td>Pay Adedi:</td><td style="text-align:right;"><b>{ortak.get('pay',0)} Pay</b></td></tr>
            <tr><td>Tarih:</td><td style="text-align:right;"><b>{bugun.strftime('%d-%m-%Y')}</b></td></tr>
        </table>
        <div style="background:#e2e8f0; padding:12px; border-radius:5px; margin-bottom:15px; text-align:center;">
            <p style="margin:0;">Toplam Tahsilat: <b>{odenmis:,.0f} TL</b></p>
        </div>
        <div style="text-align:center; padding:15px; background:#fef2f2; border-radius:5px; border: 1px solid #fecaca;">
            <span style="color:#991b1b; font-weight:bold;">KALAN BORÇ:</span><br>
            <b style="color:#dc2626; font-size:24px;">{kalan:,.0f} TL</b>
        </div>
        <div style="text-align:center; font-size:13px; margin-top:10px;">{durum_notu}</div>
    </div>
    """

# ==========================================
# 3. WEB ARAYÜZÜ (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Gayrimenkul Portföy Sistemi", layout="wide")

if not st.session_state.login_status:
    st.title("🏢 Gayrimenkul İşletme Ortaklığı Portalı")
    l_tab, f_tab = st.tabs(["🔐 Sisteme Giriş", "🔄 Şifremi Unuttum"])
    
    with l_tab:
        c_tc = st.text_input("TC Kimlik Numarası")
        c_sif = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP"):
            if c_tc == "admin" and c_sif == "admin":
                st.session_state.login_status = True
                st.session_state.user_type = "admin"
                st.rerun()
            else:
                for p_ad, p_data in st.session_state.sistem["projeler"].items():
                    for o in p_data.get("ortaklar", []):
                        if o.get("tc") == c_tc and o.get("sifre") == c_sif:
                            st.session_state.login_status = True
                            st.session_state.user_type = "ortak"
                            st.session_state.user_data = {"o": o, "p_ad": p_ad}
                            st.rerun()
                st.error("Giriş başarısız. Lütfen bilgilerinizi kontrol edin.")
    
    with f_tab:
        st.write("Şifre sıfırlama için TC ve Mail adresinizi giriniz.")
        st.info("Demo Modu: Kod ekrana yazdırılacaktır.")

# --- YÖNETİCİ PANELİ ---
elif st.session_state.user_type == "admin":
    st.sidebar.title("👑 Yönetici Paneli")
    if st.sidebar.button("🚪 Güvenli Çıkış"):
        st.session_state.login_status = False
        st.rerun()

    tabs = st.tabs(["⚙️ Ayarlar", "✍️ Veri Girişi", "📈 Dashboard", "👥 Ortaklar", "📋 Kasa/Tablo", "✅ Tahsilat", "🛠️ Operasyon", "📖 Karar Defteri"])

    # 1. AYARLAR (Proje Yönetimi)
    with tabs[0]:
        st.header("🏗️ Proje Kurulum ve Yönetim")
        v_ad = st.text_input("Proje Adı")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            v_borc = st.number_input("Toplam Beklenen Alacak (TL)", value=0.0)
            v_yil = st.selectbox("Başlama Yılı", [2025, 2026, 2027], index=1)
        with col_m2:
            v_pesin1 = st.number_input("1. Peşinat Tutarı", value=0.0)
            v_taksay = st.number_input("Taksit Sayısı", value=19)
        
        if st.button("SİSTEMİ KUR VE KAYDET"):
            plan, etiketler = takvim_hesapla(v_yil, 5, int(v_taksay), v_pesin1, 0, 0, 0, 0)
            st.session_state.sistem["projeler"][v_ad] = {
                "ad": v_ad, "toplam_maliyet": v_borc, "toplam_pay": 100,
                "plan": plan, "etiketler": etiketler, "ortaklar": [], "kasadan_cikan": 0.0, "kasa_log": [], "kararlar": []
            }
            veriyi_kaydet(st.session_state.sistem)
            st.success(f"{v_ad} projesi başarıyla kuruldu.")

    # 4. ORTAKLAR LİSTESİ & MAKBÜZ
    with tabs[3]:
        p_list_sec = st.selectbox("Proje Seç", list(st.session_state.sistem["projeler"].keys()), key="p_list")
        if p_list_sec:
            p_data = st.session_state.sistem["projeler"][p_list_sec]
            st.subheader(f"👥 {p_list_sec} Ortaklar Listesi")
            st.write("Burada tüm ortakların temerrüt durumlarını ve toplam borçlarını görebilirsiniz.")
            # Makbuz butonu
            o_makbuz_sec = st.selectbox("Makbuz Üretilecek Ortak", [o["ad"] for o in p_data["ortaklar"]])
            if st.button("📄 MAKBUZ GÖRÜNTÜLE"):
                st.markdown(makbuz_olustur_html(p_list_sec, o_makbuz_sec), unsafe_allow_html=True)

    # 8. KARAR DEFTERİ
    with tabs[7]:
        p_k_sec = st.selectbox("Karar Defteri Projesi", list(st.session_state.sistem["projeler"].keys()), key="p_karar")
        if p_k_sec:
            k_no = st.text_input("Karar Numarası")
            k_gun = st.text_area("Gündem Maddesi")
            k_metin = st.text_area("Karar Detayı")
            if st.button("KARARI DEFTERE İŞLE"):
                st.session_state.sistem["projeler"][p_k_sec].setdefault("kararlar", []).append({
                    "no": k_no, "gundem": k_gun, "metin": k_metin, "tarih": str(date.today()), "sonuc": "ONAYLANDI"
                })
                veriyi_kaydet(st.session_state.sistem)
                st.success("Karar kaydedildi.")

# --- ORTAK PANELİ ---
elif st.session_state.user_type == "ortak":
    u = st.session_state.user_data
    st.title(f"👋 Merhaba, {u['o']['ad']}")
    if st.sidebar.button("🚪 Çıkış Yap"):
        st.session_state.login_status = False
        st.rerun()

    st.markdown(makbuz_olustur_html(u['p_ad'], u['o']['ad']), unsafe_allow_html=True)
    
    st.subheader("🗓️ Ödeme Planı Takibi")
    # Taksitleri listeleyen tablo
    st.table(u['o']['plan'])