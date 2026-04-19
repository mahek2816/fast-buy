# 🛒 Fast Buy - E-Commerce Web Application

## 🚀 Overview

Fast Buy is a full-stack e-commerce web application developed using Flask. It allows users to browse products, add items to cart, and simulate an online shopping experience.

---

## ✨ Features

* 🔐 User Login & Registration
* 🛍️ Product Listing
* 🛒 Add to Cart Functionality
* 📦 Order Simulation (Demo)
* 💾 MySQL Database Integration
* 📱 Responsive Design

---

## 🛠️ Tech Stack

* **Backend:** Python (Flask)
* **Frontend:** HTML, CSS, JavaScript
* **Database:** MySQL
* **Tools:** Git, GitHub

---

## 📂 Project Structure

```text
fast-buy/
│── app.py                 # Main Flask application
│── database.sql          # MySQL database export
│── requirements.txt      # Dependencies (optional)

├── templates/  ->all templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── cart.html
│   ├── product.html
│   └── checkout.html
     
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   ├── js/
│   │   └── script.js
        └── main.js
│   │
│   └── images/
│       ├── product1.jpg
│       ├── product2.jpg
│       └── ...
│   │
│   │
│   └── categories/
│       ├── bath.avif
│       ├── beauty.jpg
│       └── ...
│   │
│   └── products/
│       ├── pro1.jpg
│       ├── pro2.jpg
│       └── ...
├── .gitignore
└── README.md
```

---

## ▶️ How to Run

1. Install required libraries

   ```
   pip install flask mysql-connector-python
   ```

2. Setup Database

   * Open MySQL
   * Import `database.sql`

3. Run the application

   ```
   python app.py
   ```

4. Open in browser

   ```
   http://127.0.0.1:5000/
   ```

---

## 🎯 Purpose

This project demonstrates backend development, database integration, and real-world web application development using Flask.

---

## 👨‍💻 Author

**Mahek Pithadiya**
Python Developer

---

## ⭐ Note

This is a demo project created for learning and showcasing development skills.
