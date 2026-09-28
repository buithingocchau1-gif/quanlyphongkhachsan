import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

# ============================================================
# CẤU HÌNH
# ============================================================

st.set_page_config(
    page_title="Hotel Management System",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "hotel_management.db"


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


conn = get_connection()


def init_database():
    cur = conn.cursor()

    # Phòng
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            floor INTEGER,
            price REAL DEFAULT 0,
            status TEXT DEFAULT 'Trống',
            notes TEXT
        )
    """)

    # Khách hàng
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            nationality TEXT,
            preferences TEXT,
            stay_count INTEGER DEFAULT 0,
            feedback TEXT,
            created_at TEXT
        )
    """)

    # Booking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE,
            customer_id INTEGER,
            room_id INTEGER,
            check_in TEXT,
            check_out TEXT,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            special_request TEXT,
            booking_source TEXT,
            room_price REAL,
            discount REAL DEFAULT 0,
            deposit REAL DEFAULT 0,
            status TEXT DEFAULT 'Đã đặt',
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        )
    """)

    # Dịch vụ
    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            service_name TEXT,
            quantity INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(booking_id) REFERENCES bookings(id)
        )
    """)

    # Housekeeping
    cur.execute("""
        CREATE TABLE IF NOT EXISTS housekeeping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            staff_name TEXT,
            task TEXT,
            status TEXT DEFAULT 'Chưa làm',
            created_at TEXT,
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        )
    """)

    # Khuyến mãi
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            description TEXT,
            discount_percent REAL DEFAULT 0,
            start_date TEXT,
            end_date TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    # Giá theo ngày
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dynamic_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_type TEXT,
            price_date TEXT,
            price REAL
        )
    """)

    conn.commit()


init_database()


# ============================================================
# HÀM DATABASE
# ============================================================

def query_df(sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


def execute(sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    return cur.lastrowid


def money(value):
    return f"{value:,.0f} VNĐ"


def nights(check_in, check_out):
    return max((check_out - check_in).days, 1)


def room_is_available(room_id, check_in, check_out, exclude_booking=None):
    sql = """
        SELECT *
        FROM bookings
        WHERE room_id = ?
        AND status NOT IN ('Đã hủy', 'Đã trả phòng')
        AND date(check_in) < date(?)
        AND date(check_out) > date(?)
    """

    params = [room_id, check_out.isoformat(), check_in.isoformat()]

    if exclude_booking:
        sql += " AND id != ?"
        params.append(exclude_booking)

    result = query_df(sql, params)

    return result.empty


def get_room_price(room_type, target_date, default_price):
    result = query_df("""
        SELECT price
        FROM dynamic_prices
        WHERE room_type = ?
        AND price_date = ?
        ORDER BY id DESC
        LIMIT 1
    """, (room_type, target_date.isoformat()))

    if not result.empty:
        return float(result.iloc[0]["price"])

    return default_price


def calculate_booking_total(booking_id):
    booking = query_df("""
        SELECT *
        FROM bookings
        WHERE id = ?
    """, (booking_id,))

    if booking.empty:
        return 0

    b = booking.iloc[0]

    check_in = datetime.strptime(
        b["check_in"], "%Y-%m-%d"
    ).date()

    check_out = datetime.strptime(
        b["check_out"], "%Y-%m-%d"
    ).date()

    room_total = float(b["room_price"]) * nights(check_in, check_out)

    discount = float(b["discount"] or 0)

    service_df = query_df("""
        SELECT SUM(quantity * unit_price) AS total
        FROM services
        WHERE booking_id = ?
    """, (booking_id,))

    service_total = (
        float(service_df.iloc[0]["total"])
        if not service_df.empty and service_df.iloc[0]["total"]
        else 0
    )

    return room_total + service_total - discount


def generate_booking_code():
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"BK{now}"


# ============================================================
# DỮ LIỆU MẪU
# ============================================================

def seed_rooms():

    count = query_df("SELECT COUNT(*) AS total FROM rooms").iloc[0]["total"]

    if count > 0:
        return

    rooms = []

    room_types = [
        ("Standard", 500000),
        ("Deluxe", 750000),
        ("Suite", 1200000),
        ("Family", 1500000)
    ]

    room_number = 101

    for floor in range(1, 6):
        for i in range(4):
            room_type, price = room_types[i]
            rooms.append(
                (
                    str(room_number),
                    room_type,
                    floor,
                    price,
                    "Trống",
                    ""
                )
            )
            room_number += 1

    conn.executemany("""
        INSERT INTO rooms
        (room_number, room_type, floor, price, status, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rooms)

    conn.commit()


seed_rooms()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🏨 HOTEL MANAGEMENT")

st.sidebar.markdown(
    "### Hệ thống quản lý khách sạn"
)

page = st.sidebar.radio(
    "MENU",
    [
        "📊 Dashboard",
        "🏨 Phòng & Inventory",
        "📅 Đặt phòng & CRM",
        "💰 Giá & Khuyến mãi",
        "📈 Báo cáo",
        "🧹 Housekeeping",
        "🍽️ POS & Dịch vụ",
        "🌐 Channel Manager"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "Hotel Management System\n"
    "Streamlit + SQLite"
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "📊 Dashboard":

    st.title("📊 Tổng quan khách sạn")

    rooms = query_df("SELECT * FROM rooms")

    today = date.today()

    active_bookings = query_df("""
        SELECT *
        FROM bookings
        WHERE status NOT IN ('Đã hủy', 'Đã trả phòng')
        AND date(check_in) <= date(?)
        AND date(check_out) > date(?)
    """, (today.isoformat(), today.isoformat()))

    total_rooms = len(rooms)
    occupied = len(active_bookings)

    available = total_rooms - occupied

    occupancy = (
        occupied / total_rooms * 100
        if total_rooms
        else 0
    )

    revenue_df = query_df("""
        SELECT SUM(room_price) AS revenue
        FROM bookings
        WHERE status != 'Đã hủy'
    """)

    room_revenue = (
        revenue_df.iloc[0]["revenue"]
        if revenue_df.iloc[0]["revenue"]
        else 0
    )

    service_df = query_df("""
        SELECT SUM(quantity * unit_price) AS revenue
        FROM services
    """)

    service_revenue = (
        service_df.iloc[0]["revenue"]
        if service_df.iloc[0]["revenue"]
        else 0
    )

    total_revenue = room_revenue + service_revenue

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🏨 Tổng số phòng",
        total_rooms
    )

    c2.metric(
        "🛏️ Phòng đang ở",
        occupied
    )

    c3.metric(
        "🟢 Phòng còn trống",
        available
    )

    c4.metric(
        "📊 Công suất",
        f"{occupancy:.1f}%"
    )

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("💰 Doanh thu")

        st.metric(
            "Tổng doanh thu",
            money(total_revenue)
        )

    with c2:
        st.subheader("📅 Booking hiện tại")

        st.metric(
            "Số booking",
            len(active_bookings)
        )

    st.divider()

    st.subheader("🏨 Trạng thái phòng")

    room_display = rooms.copy()

    room_display["Hiển thị"] = room_display.apply(
        lambda x:
        f"Phòng {x['room_number']} - {x['room_type']}",
        axis=1
    )

    cols = st.columns(4)

    for i, room in room_display.iterrows():

        room_id = room["id"]

        booking = query_df("""
            SELECT *
            FROM bookings
            WHERE room_id = ?
            AND status NOT IN ('Đã hủy', 'Đã trả phòng')
            AND date(check_in) <= date(?)
            AND date(check_out) > date(?)
        """, (
            room_id,
            today.isoformat(),
            today.isoformat()
        ))

        if not booking.empty:
            status = "🔴 Đang có khách"
        elif room["status"] == "Chờ dọn dẹp":
            status = "🟡 Chờ dọn"
        elif room["status"] == "Đang sửa chữa":
            status = "🛠️ Đang sửa"
        else:
            status = "🟢 Trống"

        with cols[i % 4]:
            st.info(
                f"**Phòng {room['room_number']}**\n\n"
                f"{room['room_type']}\n\n"
                f"{status}"
            )


# ============================================================
# ROOM & INVENTORY
# ============================================================

elif page == "🏨 Phòng & Inventory":

    st.title("🏨 Quản lý phòng & Inventory")

    tab1, tab2 = st.tabs([
        "Room Matrix",
        "Quản lý phòng"
    ])

    with tab1:

        st.subheader("🗺️ Room Matrix")

        rooms = query_df("""
            SELECT *
            FROM rooms
            ORDER BY floor, room_number
        """)

        today = date.today()

        for _, room in rooms.iterrows():

            booking = query_df("""
                SELECT *
                FROM bookings
                WHERE room_id = ?
                AND status NOT IN ('Đã hủy', 'Đã trả phòng')
                AND date(check_in) <= date(?)
                AND date(check_out) > date(?)
            """, (
                room["id"],
                today.isoformat(),
                today.isoformat()
            ))

            if not booking.empty:
                status = "🔴 Đang có khách"
            elif room["status"] == "Chờ dọn dẹp":
                status = "🟡 Chờ dọn dẹp"
            elif room["status"] == "Đang sửa chữa":
                status = "🛠️ Đang sửa chữa"
            else:
                status = "🟢 Trống"

            st.write(
                f"**Phòng {room['room_number']}** | "
                f"{room['room_type']} | "
                f"{money(room['price'])} | "
                f"{status}"
            )

    with tab2:

        st.subheader("⚙️ Cập nhật trạng thái phòng")

        rooms = query_df(
            "SELECT * FROM rooms ORDER BY room_number"
        )

        room_choice = st.selectbox(
            "Chọn phòng",
            rooms["id"],
            format_func=lambda x:
            f"Phòng {rooms[rooms.id == x].iloc[0]['room_number']}"
        )

        status = st.selectbox(
            "Trạng thái",
            [
                "Trống",
                "Chờ dọn dẹp",
                "Đang sửa chữa"
            ]
        )

        note = st.text_input("Ghi chú")

        if st.button(
            "💾 Cập nhật phòng",
            type="primary"
        ):

            execute("""
                UPDATE rooms
                SET status = ?, notes = ?
                WHERE id = ?
            """, (
                status,
                note,
                room_choice
            ))

            st.success("Đã cập nhật phòng!")
            st.rerun()


# ============================================================
# BOOKING & CRM
# ============================================================

elif page == "📅 Đặt phòng & CRM":

    st.title("📅 Đặt phòng & CRM")

    tab1, tab2, tab3 = st.tabs([
        "➕ Tạo Booking",
        "📋 Danh sách Booking",
        "👤 Hồ sơ khách hàng"
    ])

    with tab1:

        st.subheader("Tạo booking mới / Walk-in")

        with st.form("booking_form"):

            col1, col2 = st.columns(2)

            with col1:

                name = st.text_input(
                    "Tên khách hàng *"
                )

                phone = st.text_input(
                    "Số điện thoại"
                )

                email = st.text_input(
                    "Email"
                )

                nationality = st.text_input(
                    "Quốc tịch"
                )

                adults = st.number_input(
                    "Số người lớn",
                    min_value=1,
                    value=1
                )

            with col2:

                rooms = query_df("""
                    SELECT *
                    FROM rooms
                    ORDER BY room_number
                """)

                room_id = st.selectbox(
                    "Chọn phòng",
                    rooms["id"],
                    format_func=lambda x:
                    f"Phòng {rooms[rooms.id == x].iloc[0]['room_number']} - "
                    f"{rooms[rooms.id == x].iloc[0]['room_type']}"
                )

                check_in = st.date_input(
                    "Check-in",
                    value=date.today()
                )

                check_out = st.date_input(
                    "Check-out",
                    value=date.today() + timedelta(days=1)
                )

                children = st.number_input(
                    "Trẻ em",
                    min_value=0,
                    value=0
                )

                source = st.selectbox(
                    "Nguồn booking",
                    [
                        "Walk-in",
                        "Website",
                        "Điện thoại",
                        "Agoda",
                        "Booking.com",
                        "Traveloka"
                    ]
                )

            special_request = st.text_area(
                "Yêu cầu đặc biệt",
                placeholder=
                "Không hút thuốc, tầng cao, nôi em bé..."
            )

            submit = st.form_submit_button(
                "🏨 Tạo Booking",
                type="primary"
            )

            if submit:

                if check_out <= check_in:
                    st.error(
                        "Ngày check-out phải sau check-in."
                    )
                elif not room_is_available(
                    room_id,
                    check_in,
                    check_out
                ):
                    st.error(
                        "❌ Phòng này đã có booking trong khoảng thời gian trên."
                    )
                else:

                    selected_room = rooms[
                        rooms["id"] == room_id
                    ].iloc[0]

                    room_price = get_room_price(
                        selected_room["room_type"],
                        check_in,
                        selected_room["price"]
                    )

                    customer_id = execute("""
                        INSERT INTO customers
                        (
                            name,
                            phone,
                            email,
                            nationality,
                            preferences,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        name,
                        phone,
                        email,
                        nationality,
                        special_request,
                        datetime.now().isoformat()
                    ))

                    booking_code = generate_booking_code()

                    execute("""
                        INSERT INTO bookings
                        (
                            booking_code,
                            customer_id,
                            room_id,
                            check_in,
                            check_out,
                            adults,
                            children,
                            special_request,
                            booking_source,
                            room_price,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        booking_code,
                        customer_id,
                        room_id,
                        check_in.isoformat(),
                        check_out.isoformat(),
                        adults,
                        children,
                        special_request,
                        source,
                        room_price,
                        datetime.now().isoformat()
                    ))

                    st.success(
                        f"✅ Tạo booking thành công: {booking_code}"
                    )

    with tab2:

        st.subheader("📋 Danh sách Booking")

        bookings = query_df("""
            SELECT
                b.id,
                b.booking_code,
                c.name AS customer,
                c.phone,
                r.room_number,
                r.room_type,
                b.check_in,
                b.check_out,
                b.booking_source,
                b.status,
                b.deposit
            FROM bookings b
            LEFT JOIN customers c
                ON b.customer_id = c.id
            LEFT JOIN rooms r
                ON b.room_id = r.id
            ORDER BY b.id DESC
        """)

        if bookings.empty:
            st.info("Chưa có booking.")
        else:

            st.dataframe(
                bookings,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            booking_id = st.selectbox(
                "Chọn booking để cập nhật",
                bookings["id"],
                format_func=lambda x:
                bookings[bookings.id == x].iloc[0]["booking_code"]
            )

            new_status = st.selectbox(
                "Trạng thái mới",
                [
                    "Đã đặt",
                    "Đã check-in",
                    "Đã trả phòng",
                    "Đã hủy"
                ]
            )

            deposit = st.number_input(
                "Tiền cọc",
                min_value=0.0,
                value=0.0,
                step=100000.0
            )

            if st.button(
                "Cập nhật Booking"
            ):

                execute("""
                    UPDATE bookings
                    SET status = ?, deposit = ?
                    WHERE id = ?
                """, (
                    new_status,
                    deposit,
                    booking_id
                ))

                st.success(
                    "Đã cập nhật booking."
                )
                st.rerun()

    with tab3:

        st.subheader("👤 Customer Profile")

        customers = query_df("""
            SELECT *
            FROM customers
            ORDER BY id DESC
        """)

        if not customers.empty:

            st.dataframe(
                customers,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            customer_id = st.selectbox(
                "Chọn khách hàng",
                customers["id"],
                format_func=lambda x:
                customers[customers.id == x].iloc[0]["name"]
            )

            feedback = st.text_area(
                "Phản hồi / ghi chú khách hàng"
            )

            if st.button(
                "💾 Lưu hồ sơ khách"
            ):

                execute("""
                    UPDATE customers
                    SET feedback = ?,
                        stay_count = stay_count + 1
                    WHERE id = ?
                """, (
                    feedback,
                    customer_id
                ))

                st.success(
                    "Đã cập nhật hồ sơ khách hàng."
                )
                st.rerun()


# ============================================================
# DYNAMIC PRICING & PROMOS
# ============================================================

elif page == "💰 Giá & Khuyến mãi":

    st.title("💰 Dynamic Pricing & Promotions")

    tab1, tab2 = st.tabs([
        "💵 Giá linh hoạt",
        "🎁 Khuyến mãi"
    ])

    with tab1:

        st.subheader(
            "Thiết lập giá theo ngày"
        )

        rooms = query_df("""
            SELECT DISTINCT room_type
            FROM rooms
        """)

        room_type = st.selectbox(
            "Loại phòng",
            rooms["room_type"].tolist()
        )

        price_date = st.date_input(
            "Ngày áp dụng",
            value=date.today()
        )

        price = st.number_input(
            "Giá phòng",
            min_value=0.0,
            value=500000.0,
            step=50000.0
        )

        if st.button(
            "💾 Lưu giá"
        ):

            execute("""
                INSERT INTO dynamic_prices
                (
                    room_type,
                    price_date,
                    price
                )
                VALUES (?, ?, ?)
            """, (
                room_type,
                price_date.isoformat(),
                price
            ))

            st.success(
                "Đã thiết lập giá."
            )

        prices = query_df("""
            SELECT *
            FROM dynamic_prices
            ORDER BY price_date DESC
        """)

        if not prices.empty:
            st.dataframe(
                prices,
                use_container_width=True,
                hide_index=True
            )

    with tab2:

        st.subheader(
            "🎁 Tạo mã khuyến mãi"
        )

        with st.form("promo_form"):

            code = st.text_input(
                "Mã giảm giá"
            ).upper()

            description = st.text_input(
                "Mô tả"
            )

            discount = st.number_input(
                "Giảm (%)",
                min_value=0.0,
                max_value=100.0,
                value=10.0
            )

            start = st.date_input(
                "Ngày bắt đầu"
            )

            end = st.date_input(
                "Ngày kết thúc",
                value=date.today() + timedelta(days=30)
            )

            create = st.form_submit_button(
                "🎁 Tạo khuyến mãi"
            )

            if create:

                if not code:
                    st.error(
                        "Vui lòng nhập mã."
                    )
                else:

                    try:

                        execute("""
                            INSERT INTO promos
                            (
                                code,
                                description,
                                discount_percent,
                                start_date,
                                end_date
                            )
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            code,
                            description,
                            discount,
                            start.isoformat(),
                            end.isoformat()
                        ))

                        st.success(
                            "Đã tạo chương trình."
                        )

                    except sqlite3.IntegrityError:
                        st.error(
                            "Mã khuyến mãi đã tồn tại."
                        )

        promos = query_df("""
            SELECT *
            FROM promos
            ORDER BY id DESC
        """)

        if not promos.empty:

            st.dataframe(
                promos,
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# REPORTS
# ============================================================

elif page == "📈 Báo cáo":

    st.title("📈 Báo cáo tài chính & vận hành")

    rooms = query_df(
        "SELECT COUNT(*) AS total FROM rooms"
    )

    total_rooms = int(
        rooms.iloc[0]["total"]
    )

    bookings = query_df("""
        SELECT *
        FROM bookings
        WHERE status != 'Đã hủy'
    """)

    services = query_df("""
        SELECT *
        FROM services
    """)

    room_revenue = 0

    for _, b in bookings.iterrows():

        try:

            ci = datetime.strptime(
                b["check_in"],
                "%Y-%m-%d"
            ).date()

            co = datetime.strptime(
                b["check_out"],
                "%Y-%m-%d"
            ).date()

            room_revenue += (
                float(b["room_price"])
                * nights(ci, co)
            )

        except:
            pass

    service_revenue = (
        (services["quantity"] * services["unit_price"]).sum()
        if not services.empty
        else 0
    )

    total_revenue = room_revenue + service_revenue

    today = date.today()

    active = query_df("""
        SELECT *
        FROM bookings
        WHERE status NOT IN ('Đã hủy', 'Đã trả phòng')
        AND date(check_in) <= date(?)
        AND date(check_out) > date(?)
    """, (
        today.isoformat(),
        today.isoformat()
    ))

    occupied = len(active)

    occupancy = (
        occupied / total_rooms * 100
        if total_rooms
        else 0
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "💰 Doanh thu",
        money(total_revenue)
    )

    c2.metric(
        "📊 Công suất phòng",
        f"{occupancy:.1f}%"
    )

    c3.metric(
        "📅 Tổng booking",
        len(bookings)
    )

    st.divider()

    st.subheader(
        "💵 Chi tiết doanh thu"
    )

    report = pd.DataFrame({
        "Nguồn": [
            "Tiền phòng",
            "Dịch vụ",
            "Tổng cộng"
        ],
        "Doanh thu": [
            room_revenue,
            service_revenue,
            total_revenue
        ]
    })

    st.dataframe(
        report,
        use_container_width=True,
        hide_index=True
    )

    st.bar_chart(
        report.set_index("Nguồn")
    )


# ============================================================
# HOUSEKEEPING
# ============================================================

elif page == "🧹 Housekeeping":

    st.title("🧹 Quản lý Housekeeping")

    tab1, tab2 = st.tabs([
        "➕ Phân công",
        "📋 Danh sách công việc"
    ])

    with tab1:

        rooms = query_df("""
            SELECT *
            FROM rooms
            ORDER BY room_number
        """)

        room_id = st.selectbox(
            "Phòng",
            rooms["id"],
            format_func=lambda x:
            f"Phòng {rooms[rooms.id == x].iloc[0]['room_number']}"
        )

        staff = st.text_input(
            "Tên nhân viên"
        )

        task = st.selectbox(
            "Công việc",
            [
                "Dọn phòng sau check-out",
                "Vệ sinh phòng",
                "Bổ sung minibar",
                "Kiểm tra thiết bị",
                "Tổng vệ sinh"
            ]
        )

        if st.button(
            "🧹 Phân công"
        ):

            execute("""
                INSERT INTO housekeeping
                (
                    room_id,
                    staff_name,
                    task,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                room_id,
                staff,
                task,
                "Chưa làm",
                datetime.now().isoformat()
            ))

            execute("""
                UPDATE rooms
                SET status = 'Chờ dọn dẹp'
                WHERE id = ?
            """, (room_id,))

            st.success(
                "Đã phân công Housekeeping."
            )

    with tab2:

        tasks = query_df("""
            SELECT
                h.id,
                r.room_number,
                h.staff_name,
                h.task,
                h.status,
                h.created_at
            FROM housekeeping h
            LEFT JOIN rooms r
                ON h.room_id = r.id
            ORDER BY h.id DESC
        """)

        if not tasks.empty:

            st.dataframe(
                tasks,
                use_container_width=True,
                hide_index=True
            )

            task_id = st.selectbox(
                "Chọn công việc",
                tasks["id"]
            )

            task_status = st.selectbox(
                "Trạng thái",
                [
                    "Chưa làm",
                    "Đang làm",
                    "Hoàn thành"
                ]
            )

            if st.button(
                "✅ Cập nhật công việc"
            ):

                execute("""
                    UPDATE housekeeping
                    SET status = ?
                    WHERE id = ?
                """, (
                    task_status,
                    task_id
                ))

                if task_status == "Hoàn thành":

                    room_id_df = query_df("""
                        SELECT room_id
                        FROM housekeeping
                        WHERE id = ?
                    """, (task_id,))

                    if not room_id_df.empty:

                        execute("""
                            UPDATE rooms
                            SET status = 'Trống'
                            WHERE id = ?
                        """, (
                            int(room_id_df.iloc[0]["room_id"]),
                        ))

                st.success(
                    "Đã cập nhật."
                )

                st.rerun()


# ============================================================
# POS & SERVICES
# ============================================================

elif page == "🍽️ POS & Dịch vụ":

    st.title("🍽️ POS & Dịch vụ")

    bookings = query_df("""
        SELECT
            b.id,
            b.booking_code,
            c.name,
            r.room_number
        FROM bookings b
        LEFT JOIN customers c
            ON b.customer_id = c.id
        LEFT JOIN rooms r
            ON b.room_id = r.id
        WHERE b.status IN
        ('Đã đặt', 'Đã check-in')
        ORDER BY b.id DESC
    """)

    if bookings.empty:

        st.info(
            "Chưa có booking đang hoạt động."
        )

    else:

        booking_id = st.selectbox(
            "Chọn booking / phòng",
            bookings["id"],
            format_func=lambda x:
            f"Phòng {bookings[bookings.id == x].iloc[0]['room_number']} - "
            f"{bookings[bookings.id == x].iloc[0]['name']}"
        )

        service_name = st.selectbox(
            "Dịch vụ",
            [
                "Ăn sáng",
                "Nhà hàng",
                "Minibar",
                "Giặt là",
                "Spa",
                "Đưa đón sân bay",
                "Thuê xe",
                "Khác"
            ]
        )

        quantity = st.number_input(
            "Số lượng",
            min_value=1,
            value=1
        )

        unit_price = st.number_input(
            "Đơn giá",
            min_value=0.0,
            value=50000.0,
            step=10000.0
        )

        if st.button(
            "➕ Thêm vào hóa đơn",
            type="primary"
        ):

            execute("""
                INSERT INTO services
                (
                    booking_id,
                    service_name,
                    quantity,
                    unit_price,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                booking_id,
                service_name,
                quantity,
                unit_price,
                datetime.now().isoformat()
            ))

            st.success(
                "Đã thêm dịch vụ vào hóa đơn phòng."
            )

        st.divider()

        st.subheader(
            "🧾 Hóa đơn"
        )

        selected_services = query_df("""
            SELECT
                service_name,
                quantity,
                unit_price,
                quantity * unit_price AS total
            FROM services
            WHERE booking_id = ?
        """, (booking_id,))

        if not selected_services.empty:

            st.dataframe(
                selected_services,
                use_container_width=True,
                hide_index=True
            )

        total = calculate_booking_total(
            booking_id
        )

        booking_info = query_df("""
            SELECT
                room_price,
                check_in,
                check_out,
                deposit
            FROM bookings
            WHERE id = ?
        """, (booking_id,))

        if not booking_info.empty:

            b = booking_info.iloc[0]

            ci = datetime.strptime(
                b["check_in"],
                "%Y-%m-%d"
            ).date()

            co = datetime.strptime(
                b["check_out"],
                "%Y-%m-%d"
            ).date()

            room_total = (
                float(b["room_price"])
                * nights(ci, co)
            )

            st.write(
                f"Tiền phòng: **{money(room_total)}**"
            )

            st.write(
                f"Tiền cọc: **{money(float(b['deposit'] or 0))}**"
            )

            st.subheader(
                f"💰 Tổng thanh toán: {money(total)}"
            )


# ============================================================
# CHANNEL MANAGER
# ============================================================

elif page == "🌐 Channel Manager":

    st.title("🌐 Channel Manager")

    st.info(
        "Đây là module mô phỏng đồng bộ tồn phòng. "
        "Khi triển khai thực tế cần kết nối API của từng OTA."
    )

    rooms = query_df("""
        SELECT
            room_type,
            COUNT(*) AS total
        FROM rooms
        GROUP BY room_type
    """)

    today = date.today()

    booking_count = query_df("""
        SELECT
            r.room_type,
            COUNT(*) AS booked
        FROM bookings b
        JOIN rooms r
            ON b.room_id = r.id
        WHERE b.status NOT IN
        ('Đã hủy', 'Đã trả phòng')
        AND date(b.check_in) <= date(?)
        AND date(b.check_out) > date(?)
        GROUP BY r.room_type
    """, (
        today.isoformat(),
        today.isoformat()
    ))

    inventory = rooms.copy()

    inventory["booked"] = 0

    for i, row in inventory.iterrows():

        match = booking_count[
            booking_count["room_type"]
            == row["room_type"]
        ]

        if not match.empty:
            inventory.loc[i, "booked"] = int(
                match.iloc[0]["booked"]
            )

    inventory["available"] = (
        inventory["total"]
        - inventory["booked"]
    )

    inventory["Agoda"] = inventory["available"]
    inventory["Booking.com"] = inventory["available"]
    inventory["Traveloka"] = inventory["available"]

    st.subheader(
        "📦 Inventory Availability"
    )

    st.dataframe(
        inventory,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "🔄 Đồng bộ OTA"
    )

    ota = st.multiselect(
        "Chọn kênh",
        [
            "Agoda",
            "Booking.com",
            "Traveloka"
        ],
        default=[
            "Agoda",
            "Booking.com",
            "Traveloka"
        ]
    )

    if st.button(
        "🔄 Đồng bộ ngay",
        type="primary"
    ):

        if not ota:
            st.warning(
                "Hãy chọn ít nhất một OTA."
            )
        else:

            for channel in ota:
                st.success(
                    f"Đã mô phỏng đồng bộ Inventory → {channel}"
                )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    f"© {datetime.now().year} Hotel Management App"
)
