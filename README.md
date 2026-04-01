# Railway Reservation System (RES)

A simple full-stack **Railway Reservation System** built using **FastAPI**, **MySQL**, and **Vanilla JavaScript**.  
This project allows users to search trains, check seat availability, book tickets, cancel bookings, and check PNR status.  
It also includes an **admin panel** for managing trains, stations, and schedules.

---

## 🚀 Features

### User Features
- User registration and login
- JWT-based authentication
- Search trains by source, destination, and travel date
- View train details and seat availability
- Book tickets
- View booking history
- Cancel bookings
- Check PNR status

### Admin Features
- Add / update / delete stations
- Add / update / delete trains
- Add / update / delete schedules
- Manage seat availability
- View all bookings

---

## 🛠 Tech Stack

### Backend
- **Python**
- **FastAPI**
- **SQLAlchemy**
- **Pydantic**
- **JWT Authentication**
- **MySQL**

### Frontend
- **HTML5**
- **CSS3**
- **Vanilla JavaScript**
- **Fetch API / AJAX**

### Tools
- Swagger / OpenAPI documentation
- Git & GitHub

---

## 📂 Project Structure

```bash
RES/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── auth/
│   │   └── utils/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── search.html
│   ├── booking.html
│   ├── my-bookings.html
│   ├── pnr.html
│   ├── admin-dashboard.html
│   ├── css/
│   └── js/
│
└── README.md
