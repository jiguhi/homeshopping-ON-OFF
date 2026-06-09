import time
import hmac
import hashlib
import base64
import requests
import streamlit as st
import json
import os


BASE_URL = "https://api.searchad.naver.com"
SETTING_FILE = "settings.json"


def load_settings():
    if os.path.exists(SETTING_FILE):
        try:
            with open(SETTING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass

    return {
        "api_key": "",
        "secret_key": "",
        "customer_id": "",
        "adgroup_text": ""
    }


def save_settings(api_key, secret_key, customer_id, adgroup_text):
    data = {
        "api_key": api_key,
        "secret_key": secret_key,
        "customer_id": customer_id,
        "adgroup_text": adgroup_text
    }

    with open(SETTING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class Signature:
    @staticmethod
    def generate(timestamp, method, uri, secret_key):
        message = f"{timestamp}.{method}.{uri}"
        digest = hmac.new(
            secret_key.strip().encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).digest()
        return base64.b64encode(digest).decode()


def get_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(round(time.time() * 1000))
    signature = Signature.generate(timestamp, method, uri, secret_key)

    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key.strip(),
        "X-Customer": customer_id.strip(),
        "X-Signature": signature,
    }


def get_adgroup(adgroup_id, api_key, secret_key, customer_id):
    uri = f"/ncc/adgroups/{adgroup_id}"

    response = requests.get(
        BASE_URL + uri,
        headers=get_header("GET", uri, api_key, secret_key, customer_id),
        timeout=30
    )

    if response.status_code != 200:
        return None, f"GET 실패: {response.status_code}\n{response.text}"

    return response.json(), None


def update_adgroup_status(adgroup_id, turn_on, api_key, secret_key, customer_id):
    adgroup, error = get_adgroup(
        adgroup_id,
        api_key,
        secret_key,
        customer_id
    )

    if error:
        return False, error

    # userLock False = ON / True = OFF
    adgroup["userLock"] = not turn_on

    uri = f"/ncc/adgroups/{adgroup_id}"
    update_url = BASE_URL + uri + "?fields=userLock"

    response = requests.put(
        update_url,
        headers=get_header("PUT", uri, api_key, secret_key, customer_id),
        json=adgroup,
        timeout=30
    )

    if response.status_code in [200, 204]:
        return True, "완료"

    return False, f"PUT 실패: {response.status_code}\n{response.text}"


def get_status_text(adgroup_id, api_key, secret_key, customer_id):
    adgroup, error = get_adgroup(
        adgroup_id,
        api_key,
        secret_key,
        customer_id
    )

    if error:
        return "조회 실패", error

    user_lock = adgroup.get("userLock")

    if user_lock is True:
        return "OFF", None
    elif user_lock is False:
        return "ON", None
    else:
        return "알 수 없음", None


st.set_page_config(
    page_title="네이버 광고그룹 ON/OFF",
    layout="wide"
)

saved = load_settings()

st.title("네이버 검색광고 광고그룹 ON/OFF")

st.info("API 정보와 광고그룹 ID를 직접 입력하면 다음 실행 시 마지막 입력값이 자동으로 불러와집니다.")

with st.expander("API 정보 입력", expanded=True):
    api_key = st.text_input(
        "API KEY",
        value=saved.get("api_key", ""),
        type="password"
    )

    secret_key = st.text_input(
        "SECRET KEY",
        value=saved.get("secret_key", ""),
        type="password"
    )

    customer_id = st.text_input(
        "CUSTOMER ID",
        value=saved.get("customer_id", "")
    )

st.divider()

adgroup_text = st.text_area(
    "광고그룹 ID 입력",
    value=saved.get("adgroup_text", ""),
    height=220,
    placeholder="""한 줄에 하나씩 입력하세요.

예시:
grp-a001-02-000000057043852
grp-a001-02-000000057043904
grp-a001-01-000000031915099"""
)

action = st.radio(
    "작업 선택",
    ["ON", "OFF"],
    horizontal=True
)

adgroup_ids = [
    line.strip()
    for line in adgroup_text.splitlines()
    if line.strip()
]

col1, col2 = st.columns(2)

with col1:
    check_btn = st.button("현재 상태 조회", use_container_width=True)

with col2:
    run_btn = st.button(f"선택 광고그룹 {action} 실행", use_container_width=True)


def validate_inputs():
    if not api_key.strip():
        st.error("API KEY를 입력하세요.")
        st.stop()

    if not secret_key.strip():
        st.error("SECRET KEY를 입력하세요.")
        st.stop()

    if not customer_id.strip():
        st.error("CUSTOMER ID를 입력하세요.")
        st.stop()

    if not adgroup_ids:
        st.error("광고그룹 ID를 1개 이상 입력하세요.")
        st.stop()


if check_btn:
    validate_inputs()

    save_settings(
        api_key,
        secret_key,
        customer_id,
        adgroup_text
    )

    st.subheader("현재 상태 조회 결과")

    for adgroup_id in adgroup_ids:
        with st.spinner(f"{adgroup_id} 조회 중..."):
            status, error = get_status_text(
                adgroup_id,
                api_key,
                secret_key,
                customer_id
            )

        if error:
            st.error(f"{adgroup_id} → 조회 실패\n\n{error}")
        elif status == "ON":
            st.success(f"{adgroup_id} → 현재 ON")
        elif status == "OFF":
            st.warning(f"{adgroup_id} → 현재 OFF")
        else:
            st.info(f"{adgroup_id} → {status}")


if run_btn:
    validate_inputs()

    save_settings(
        api_key,
        secret_key,
        customer_id,
        adgroup_text
    )

    turn_on = action == "ON"

    st.subheader("실행 결과")

    for adgroup_id in adgroup_ids:
        with st.spinner(f"{adgroup_id} {action} 처리 중..."):
            success, message = update_adgroup_status(
                adgroup_id,
                turn_on,
                api_key,
                secret_key,
                customer_id
            )

        if success:
            st.success(f"{adgroup_id} → {action} 완료")
        else:
            st.error(f"{adgroup_id} → {action} 실패\n\n{message}")
