import streamlit as st
import sqlite3
from datetime import date, datetime

# =========================================================
# CẤU HÌNH
# =========================================================

st.set_page_config(
    page_title="Hotel Manager",
    page_icon="🏨",
    layout="wide"
)

DB_NAME = "hotel.db"


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Trống',
            note TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT,
            room_number TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            guests INTEGER DEFAULT 1,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'Đang đặt',
            created_at TEXT
        )
    """)

    conn.commit()

    # Thêm dữ liệu mẫu nếu chưa có phòng
    cursor.execute("SELECT COUNT(*) AS count FROM rooms")
    count = cursor.fetchone()["count"]

    if count == 0:
        sample_rooms = [
            ("101", "Standard", 500000, "Trống", ""),
            ("102", "Standard", 500000, "Trống", ""),
            ("201", "Deluxe", 800000, "Trống", ""),
            ("202", "Deluxe", 800000, "Đang ở", ""),
            ("301", "Suite", 1200000, "Trống", ""),
            ("302", "Suite", 1200000, "Bảo trì", "Đang sửa máy lạnh"),
            ("401", "Family", 1500000, "Đã đặt", ""),
            ("402", "Family", 1500000, "Trống", "")
        ]

        cursor.executemany("""
            INSERT INTO rooms
            (room_number, room_type, price, status, note)
            VALUES (?, ?, ?, ?, ?)
        """, sample_rooms)

        conn.commit()

    conn.close()


init_database()


# =========================================================
# HÀM DATABASE
# =========================================================

def get_rooms(search="", status="Tất cả", room_type="Tất cả"):
    conn = get_connection()

    query = "SELECT * FROM rooms WHERE 1=1"
    params = []

    if search:
        query += " AND room_number LIKE ?"
        params.append(f"%{search}%")

    if status != "Tất cả":
        query += " AND status = ?"
        params.append(status)

    if room_type != "Tất cả":
        query += " AND room_type = ?"
        params.append(room_type)

    query += " ORDER BY room_number"

    rooms = conn.execute(query, params).fetchall()
    conn.close()

    return rooms


def add_room(room_number, room_type, price, status, note):
    conn = get_connection()

    try:
        conn.execute("""
            INSERT INTO rooms
            (room_number, room_type, price, status, note)
            VALUES (?, ?, ?, ?, ?)
        """, (room_number, room_type, price, status, note))

        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False

    conn.close()
    return result


def update_room(room_id, room_number, room_type, price, status, note):
    conn = get_connection()

    try:
        conn.execute("""
            UPDATE rooms
            SET room_number = ?,
                room_type = ?,
                price = ?,
                status = ?,
                note = ?
            WHERE id = ?
        """, (
            room_number,
            room_type,
            price,
            status,
            note,
            room_id
        ))

        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False

    conn.close()
    return result


def delete_room(room_id):
    conn = get_connection()

    conn.execute(
        "DELETE FROM rooms WHERE id = ?",
        (room_id,)
    )

    conn.commit()
    conn.close()


def get_bookings():
    conn = get_connection()

    bookings = conn.execute("""
        SELECT * FROM bookings
        ORDER BY id DESC
    """).fetchall()

    conn.close()
    return bookings


def create_booking(
    customer_name,
    phone,
    room_number,
    check_in,
    check_out,
    guests,
    total
):
    conn = get_connection()

    conn.execute("""
        INSERT INTO bookings
        (
            customer_name,
            phone,
            room_number,
            check_in,
            check_out,
            guests,
            total,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_name,
        phone,
        room_number,
        check_in,
        check_out,
        guests,
        total,
        "Đang đặt",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Cập nhật trạng thái phòng
    conn.execute("""
        UPDATE rooms
        SET status = 'Đã đặt'
        WHERE room_number = ?
    """, (room_number,))

    conn.commit()
    conn.close()


def update_booking_status(booking_id, status, room_number):
    conn = get_connection()

    conn.execute("""
        UPDATE bookings
        SET status = ?
        WHERE id = ?
    """, (status, booking_id))

    if status == "Đã nhận phòng":
        conn.execute("""
            UPDATE rooms
            SET status = 'Đang ở'
            WHERE room_number = ?
        """, (room_number,))

    elif status in ["Đã trả phòng", "Đã hủy"]:
        conn.execute("""
            UPDATE rooms
            SET status = 'Trống'
            WHERE room_number = ?
        """, (room_number,))

    conn.commit()
    conn.close()


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🏨 HOTEL MANAGER")

st.sidebar.caption("Hệ thống quản lý khách sạn")

page = st.sidebar.radio(
    "MENU",
    [
        "📊 Tổng quan",
        "🛏️ Quản lý phòng",
        "📋 Đặt phòng",
        "📈 Thống kê"
    ]
)

st.sidebar.divider()
st.sidebar.info(
    "💡 Dữ liệu được lưu tự động bằng SQLite."
)


# =========================================================
# TỔNG QUAN
# =========================================================

if page == "📊 Tổng quan":

    st.title("🏨 Tổng quan khách sạn")
    st.caption("Hệ thống quản lý phòng và đặt phòng")

    rooms = get_rooms()

    total_rooms = len(rooms)
    empty_rooms = sum(r["status"] == "Trống" for r in rooms)
    booked_rooms = sum(r["status"] == "Đã đặt" for r in rooms)
    occupied_rooms = sum(r["status"] == "Đang ở" for r in rooms)
    maintenance_rooms = sum(r["status"] == "Bảo trì" for r in rooms)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("🏨 Tổng phòng", total_rooms)
    col2.metric("🟢 Phòng trống", empty_rooms)
    col3.metric("🟡 Đã đặt", booked_rooms)
    col4.metric("🔴 Đang ở", occupied_rooms)
    col5.metric("🔧 Bảo trì", maintenance_rooms)

    st.divider()

    st.subheader("📌 Tình trạng phòng")

    if total_rooms > 0:
        available_percent = round(
            empty_rooms / total_rooms * 100, 1
        )
    else:
        available_percent = 0

    st.progress(
        available_percent / 100,
        text=f"Tỷ lệ phòng trống: {available_percent}%"
    )

    st.divider()

    st.subheader("🛏️ Danh sách phòng")

    if rooms:
        for room in rooms:
            status = room["status"]

            if status == "Trống":
                icon = "🟢"
            elif status == "Đã đặt":
                icon = "🟡"
            elif status == "Đang ở":
                icon = "🔴"
            else:
                icon = "🔧"

            col1, col2, col3, col4 = st.columns(
                [1, 2, 2, 2]
            )

            col1.write(f"**{room['room_number']}**")
            col2.write(room["room_type"])
            col3.write(f"{room['price']:,.0f} VNĐ/đêm")
            col4.write(f"{icon} {status}")


# =========================================================
# QUẢN LÝ PHÒNG
# =========================================================

elif page == "🛏️ Quản lý phòng":

    st.title("🛏️ Quản lý phòng")

    tab1, tab2 = st.tabs(
        ["📋 Danh sách phòng", "➕ Thêm phòng"]
    )

    # -----------------------------------------------------
    # DANH SÁCH
    # -----------------------------------------------------

    with tab1:

        col1, col2, col3 = st.columns(3)

        search = col1.text_input(
            "🔎 Tìm số phòng",
            placeholder="Ví dụ: 101"
        )

        status_filter = col2.selectbox(
            "Trạng thái",
            [
                "Tất cả",
                "Trống",
                "Đã đặt",
                "Đang ở",
                "Bảo trì"
            ]
        )

        type_filter = col3.selectbox(
            "Loại phòng",
            [
                "Tất cả",
                "Standard",
                "Deluxe",
                "Suite",
                "Family"
            ]
        )

        rooms = get_rooms(
            search,
            status_filter,
            type_filter
        )

        st.write(f"**Tìm thấy {len(rooms)} phòng**")

        for room in rooms:

            with st.expander(
                f"🛏️ Phòng {room['room_number']} — "
                f"{room['room_type']} — "
                f"{room['status']}"
            ):

                col1, col2 = st.columns(2)

                with col1:

                    new_number = st.text_input(
                        "Số phòng",
                        value=room["room_number"],
                        key=f"number_{room['id']}"
                    )

                    new_type = st.selectbox(
                        "Loại phòng",
                        [
                            "Standard",
                            "Deluxe",
                            "Suite",
                            "Family"
                        ],
                        index=[
                            "Standard",
                            "Deluxe",
                            "Suite",
                            "Family"
                        ].index(room["room_type"]),
                        key=f"type_{room['id']}"
                    )

                    new_price = st.number_input(
                        "Giá phòng / đêm",
                        min_value=0.0,
                        value=float(room["price"]),
                        step=50000.0,
                        key=f"price_{room['id']}"
                    )

                with col2:

                    new_status = st.selectbox(
                        "Trạng thái",
                        [
                            "Trống",
                            "Đã đặt",
                            "Đang ở",
                            "Bảo trì"
                        ],
                        index=[
                            "Trống",
                            "Đã đặt",
                            "Đang ở",
                            "Bảo trì"
                        ].index(room["status"]),
                        key=f"status_{room['id']}"
                    )

                    new_note = st.text_area(
                        "Ghi chú",
                        value=room["note"] or "",
                        key=f"note_{room['id']}"
                    )

                    col_a, col_b = st.columns(2)

                    if col_a.button(
                        "💾 Lưu",
                        key=f"save_{room['id']}"
                    ):

                        success = update_room(
                            room["id"],
                            new_number,
                            new_type,
                            new_price,
                            new_status,
                            new_note
                        )

                        if success:
                            st.success(
                                "Đã cập nhật phòng!"
                            )
                            st.rerun()
                        else:
                            st.error(
                                "Số phòng đã tồn tại!"
                            )

                    if col_b.button(
                        "🗑️ Xóa",
                        key=f"delete_{room['id']}"
                    ):

                        delete_room(room["id"])
                        st.success("Đã xóa phòng!")
                        st.rerun()

    # -----------------------------------------------------
    # THÊM PHÒNG
    # -----------------------------------------------------

    with tab2:

        st.subheader("➕ Thêm phòng mới")

        with st.form("add_room_form"):

            room_number = st.text_input(
                "Số phòng",
                placeholder="Ví dụ: 501"
            )

            room_type = st.selectbox(
                "Loại phòng",
                [
                    "Standard",
                    "Deluxe",
                    "Suite",
                    "Family"
                ]
            )

            price = st.number_input(
                "Giá phòng / đêm",
                min_value=0.0,
                value=500000.0,
                step=50000.0
            )

            status = st.selectbox(
                "Trạng thái",
                [
                    "Trống",
                    "Đã đặt",
                    "Đang ở",
                    "Bảo trì"
                ]
            )

            note = st.text_area("Ghi chú")

            submit = st.form_submit_button(
                "➕ Thêm phòng"
            )

            if submit:

                if not room_number.strip():
                    st.error("Vui lòng nhập số phòng.")

                else:

                    success = add_room(
                        room_number.strip(),
                        room_type,
                        price,
                        status,
                        note
                    )

                    if success:
                        st.success(
                            f"Đã thêm phòng {room_number}!"
                        )
                        st.rerun()
                    else:
                        st.error(
                            "Số phòng này đã tồn tại!"
                        )


# =========================================================
# ĐẶT PHÒNG
# =========================================================

elif page == "📋 Đặt phòng":

    st.title("📋 Quản lý đặt phòng")

    tab1, tab2 = st.tabs(
        ["➕ Tạo đặt phòng", "📋 Danh sách đặt phòng"]
    )

    # -----------------------------------------------------
    # TẠO BOOKING
    # -----------------------------------------------------

    with tab1:

        available_rooms = get_rooms(
            status="Trống"
        )

        if not available_rooms:

            st.warning(
                "Hiện không có phòng trống."
            )

        else:

            room_options = {
                f"Phòng {r['room_number']} - "
                f"{r['room_type']} - "
                f"{r['price']:,.0f} VNĐ/đêm":
                r
                for r in available_rooms
            }

            with st.form("booking_form"):

                customer_name = st.text_input(
                    "👤 Tên khách hàng"
                )

                phone = st.text_input(
                    "📞 Số điện thoại"
                )

                selected_room = st.selectbox(
                    "🛏️ Chọn phòng",
                    list(room_options.keys())
                )

                room = room_options[selected_room]

                col1, col2 = st.columns(2)

                check_in = col1.date_input(
                    "📅 Ngày nhận phòng",
                    value=date.today()
                )

                check_out = col2.date_input(
                    "📅 Ngày trả phòng",
                    value=date.today()
                )

                guests = st.number_input(
                    "👥 Số khách",
                    min_value=1,
                    max_value=20,
                    value=2
                )

                nights = (
                    check_out - check_in
                ).days

                if nights <= 0:
                    nights = 1

                total = nights * room["price"]

                st.info(
                    f"🛏️ {nights} đêm × "
                    f"{room['price']:,.0f} VNĐ "
                    f"= **{total:,.0f} VNĐ**"
                )

                submit = st.form_submit_button(
                    "✅ Xác nhận đặt phòng"
                )

                if submit:

                    if not customer_name.strip():
                        st.error(
                            "Vui lòng nhập tên khách."
                        )

                    elif check_out <= check_in:
                        st.error(
                            "Ngày trả phòng phải sau ngày nhận phòng."
                        )

                    else:

                        create_booking(
                            customer_name.strip(),
                            phone.strip(),
                            room["room_number"],
                            check_in.isoformat(),
                            check_out.isoformat(),
                            guests,
                            total
                        )

                        st.success(
                            "🎉 Đặt phòng thành công!"
                        )

                        st.rerun()

    # -----------------------------------------------------
    # DANH SÁCH BOOKING
    # -----------------------------------------------------

    with tab2:

        bookings = get_bookings()

        if not bookings:

            st.info(
                "Chưa có dữ liệu đặt phòng."
            )

        else:

            for booking in bookings:

                with st.expander(
                    f"👤 {booking['customer_name']} "
                    f"— Phòng {booking['room_number']} "
                    f"— {booking['status']}"
                ):

                    col1, col2 = st.columns(2)

                    col1.write(
                        f"📞 **Điện thoại:** "
                        f"{booking['phone'] or '---'}"
                    )

                    col1.write(
                        f"📅 **Nhận:** "
                        f"{booking['check_in']}"
                    )

                    col1.write(
                        f"📅 **Trả:** "
                        f"{booking['check_out']}"
                    )

                    col2.write(
                        f"🛏️ **Phòng:** "
                        f"{booking['room_number']}"
                    )

                    col2.write(
                        f"👥 **Số khách:** "
                        f"{booking['guests']}"
                    )

                    col2.write(
                        f"💰 **Tổng tiền:** "
                        f"{booking['total']:,.0f} VNĐ"
                    )

                    new_status = st.selectbox(
                        "Cập nhật trạng thái",
                        [
                            "Đang đặt",
                            "Đã nhận phòng",
                            "Đã trả phòng",
                            "Đã hủy"
                        ],
                        index=[
                            "Đang đặt",
                            "Đã nhận phòng",
                            "Đã trả phòng",
                            "Đã hủy"
                        ].index(booking["status"]),
                        key=f"booking_status_{booking['id']}"
                    )

                    if st.button(
                        "🔄 Cập nhật",
                        key=f"update_booking_{booking['id']}"
                    ):

                        update_booking_status(
                            booking["id"],
                            new_status,
                            booking["room_number"]
                        )

                        st.success(
                            "Đã cập nhật!"
                        )

                        st.rerun()


# =========================================================
# THỐNG KÊ
# =========================================================

elif page == "📈 Thống kê":

    st.title("📈 Thống kê kinh doanh")

    bookings = get_bookings()
    rooms = get_rooms()

    total_revenue = sum(
        b["total"]
        for b in bookings
        if b["status"] != "Đã hủy"
    )

    completed = sum(
        b["status"] == "Đã trả phòng"
        for b in bookings
    )

    active = sum(
        b["status"] in ["Đang đặt", "Đã nhận phòng"]
        for b in bookings
    )

    total_rooms = len(rooms)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "💰 Doanh thu",
        f"{total_revenue:,.0f} VNĐ"
    )

    col2.metric(
        "📋 Tổng booking",
        len(bookings)
    )

    col3.metric(
        "✅ Đã hoàn thành",
        completed
    )

    col4.metric(
        "🔄 Đang hoạt động",
        active
    )

    st.divider()

    st.subheader("📊 Trạng thái phòng")

    status_data = {
        "Trống": 0,
        "Đã đặt": 0,
        "Đang ở": 0,
        "Bảo trì": 0
    }

    for room in rooms:
        if room["status"] in status_data:
            status_data[room["status"]] += 1

    st.bar_chart(status_data)

    st.divider()

    st.subheader("💰 Doanh thu từ các đơn đặt phòng")

    if bookings:

        revenue_data = {
            f"Booking #{b['id']}": b["total"]
            for b in bookings
            if b["status"] != "Đã hủy"
        }

        if revenue_data:
            st.bar_chart(revenue_data)

        else:
            st.info(
                "Chưa có doanh thu hợp lệ."
            )

    else:

        st.info(
            "Chưa có dữ liệu doanh thu."
        )


# =========================================================
# FOOTER
# =========================================================

st.sidebar.divider()

st.sidebar.caption(
    "🏨 Hotel Manager App"
)

st.sidebar.caption(
    "Built with Streamlit + SQLite"
)
