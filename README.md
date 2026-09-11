# Absaluminum Invoicing and Quotations System

A web-based business management application developed for **Absaluminum** to streamline the creation, management, and tracking of customer quotations, invoices, payments, and scheduled jobs.

The application is built with **Python and Streamlit**, with **Supabase/PostgreSQL** providing centralized data storage. It also integrates with **Google Apps Script and Google Drive** for document generation and storage.

---

## 📌 Overview

The **Absaluminum Invoicing and Quotations System** replaces manual quotation and invoicing workflows with a centralized digital platform.

The system allows authorized users to:

- Create customer quotations
- Manage existing quotations
- Convert quotations into invoices
- Create and manage invoices
- Track payments and outstanding balances
- Manage quotation and invoice documents
- Schedule jobs using a job calendar
- Manage application users and roles
- Store business information in a centralized Supabase database
- Generate and store documents through Google Drive/Google Apps Script

The application is designed to be lightweight, cost-effective, and suitable for deployment using free or low-cost cloud services.

---

## ✨ Features

### Quotations

- Create new quotations
- Add multiple materials/items to a quotation
- Calculate quantities, unit prices, totals, and tax
- Apply deposits
- Edit existing quotations
- Delete quotations
- View quotation documents
- Generate quotation PDFs
- Track quotation status
- Convert quotations into invoices

### Invoicing

- Generate invoices from quotations
- Create invoice details
- Track invoice totals
- Record payments
- Calculate outstanding amounts
- Update invoice status
- Prevent duplicate invoice numbers
- View invoice documents and PDFs
- Manage existing invoices

### Job Calendar

The job calendar provides an overview of scheduled work and allows users to manage jobs associated with customers and invoices.

### User Management

The application supports user management and role-based access.

Users can be associated with different groups/roles, allowing the system to control access to business information and functionality.

### Document Management

Quotation and invoice documents can be generated and stored using Google Drive and Google Apps Script.

The application stores references to generated documents so that users can access them directly from the system.

### Database

Supabase/PostgreSQL is used as the centralized database.

This provides a more reliable and scalable solution than the previous Google Sheets-based data storage approach.

---

# 🛠️ Technologies

| Technology | Purpose |
|---|---|
| Python | Application development |
| Streamlit | Web application interface |
| Supabase | Database and authentication |
| PostgreSQL | Relational database |
| Google Apps Script | Document and business-process automation |
| Google Drive | Document storage |
| Git | Version control |
| GitHub | Source-code hosting |

---

# 📂 Project Structure

The project is organized approximately as follows:

```text
AbsaluminumInvQout/
│
├── AbsaluminumInvQout/
│   │
│   ├── app.py
│   │
│   ├── Model.py
│   ├── Qout_Manag_Model.py
│   ├── Inv_Man_Model.py
│   ├── JobCalenderModel.py
│   ├── User_Model.py
│   │
│   ├── pages/
│   │   ├── Qoutation and Invoices.py
│   │   ├── Manage Qoutations.py
│   │   ├── Manage Invoices.py
│   │   └── Job Calender.py
│   │
│   ├── Images/
│   │   └── AbsAppIcon.png
│   │
│   ├── requirements.txt
│   ├── .env
│   └── README.md
│
└── .gitignore
```

> **Note:** File names may differ slightly depending on the current version of the application.

---

# 🖥️ Application Screenshots

Screenshots can be added to this section as the application develops.

## Login

![Application Login](docs/images/login.png)

The login screen authenticates users before providing access to the application.

---

## Quotations and Invoices

![Quotations and Invoices](docs/images/quotations-invoices.png)

The main quotation and invoicing interface provides access to the application's financial management functions.

---

## Create Quotation

![Create Quotation](docs/images/create-quotation.png)

Users can create quotations by entering customer information and adding materials or services.

---

## Manage Quotations

![Manage Quotations](docs/images/manage-quotations.png)

Existing quotations can be viewed, edited, deleted, and converted into invoices.

---

## Manage Invoices

![Manage Invoices](docs/images/manage-invoices.png)

Users can view invoices, monitor payments, and manage outstanding balances.

---

## Job Calendar

![Job Calendar](docs/images/job-calendar.png)

The job calendar provides an overview of scheduled customer jobs.

---

# 🗄️ Database Setup

The application uses **Supabase** as its centralized database.

Create a new Supabase project before running the application.

[Supabase](https://supabase.com/?utm_source=chatgpt.com)

After creating the project, create the required PostgreSQL tables.

The database contains tables for quotations, invoices, invoice details, users, and related business information.

## Example Database Structure

### Users

```text
users
├── user_id
├── full_names
├── contact_numbers
├── type
├── home_location
├── work_location
├── email
├── group_id
└── comments
```

### Quotations

The quotation tables contain information such as:

```text
QouteSummary
├── qoute_id
├── qout_name
├── inv_numb
├── inv_to
├── total_amount
├── payed_amount
├── oust_amount
├── status
├── qoute_doc
└── qoute_pdf
```

### Invoice Details

Invoice detail records contain individual items/materials associated with an invoice.

Typical information includes:

```text
InvoiceDetails
├── invoice_number
├── description
├── unit_price
├── quantity
└── total_amount
```

### Invoice Summary

The invoice summary stores high-level invoice information such as:

```text
InvoiceSummary
├── invoice_number
├── customer
├── total_amount
├── paid_amount
├── outstanding_amount
└── status
```

> **Important:** The exact schema should match the SQL/database version used by the application. Do not expose database passwords, API secrets, or service-role keys in the repository.

---

# 🔐 Environment Variables

Create a `.env` file in the project root.

Example:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

If Google Apps Script integration requires additional configuration, store those values in environment variables rather than directly in Python source code.

### ⚠️ Security

Never commit the following to GitHub:

```text
.env
service-account.json
private keys
Supabase service-role keys
Google credentials
API tokens
passwords
```

Add them to `.gitignore`.

Example:

```gitignore
.env
*.json
__pycache__/
*.pyc
.streamlit/secrets.toml
```

---

# 📦 Installation

## 1. Clone the Repository

Clone the project from GitHub:

```bash
git clone https://github.com/YOUR_USERNAME/AbsaluminumInvQout.git
```

Navigate to the project:

```bash
cd AbsaluminumInvQout
```

---

## 2. Create a Virtual Environment

Create a Python virtual environment:

### Windows

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

---

## 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

If `requirements.txt` has not yet been generated:

```bash
pip freeze > requirements.txt
```

---

# ⚙️ Configuration

Configure the Supabase connection using environment variables.

For example:

```python
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
```

The application can then initialize the Supabase client:

```python
from supabase import create_client

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)
```

---

# ▶️ Running the Application

Start the Streamlit application with:

```bash
streamlit run app.py
```

Streamlit will provide a local URL similar to:

```text
http://localhost:8501
```

Open the URL in your browser.

---

# 👤 User Authentication

Users must authenticate before accessing protected application functionality.

The application uses Supabase authentication and/or the application's user-management system to determine the user's permissions.

A user's role/group can determine which parts of the system they can access.

For example:

```text
User
 │
 ├── Authentication
 │
 ├── User lookup
 │
 ├── Determine group/role
 │
 └── Load permitted application functionality
```

---

# 🧾 Creating a Quotation

To create a quotation:

1. Log into the application.
2. Navigate to **Quotations and Invoices**.
3. Enter the customer information.
4. Add the required materials or services.
5. Enter the unit price.
6. Enter the quantity.
7. Review the calculated totals.
8. Apply the applicable tax.
9. Specify the required deposit.
10. Save the quotation.
11. Generate the quotation document/PDF.

Quotation information is stored in Supabase while generated documents can be stored in Google Drive.

---

# 🔄 Converting a Quotation to an Invoice

An approved quotation can be converted into an invoice.

Typical workflow:

```text
Create Quotation
       │
       ▼
Review Quotation
       │
       ▼
Approve Quotation
       │
       ▼
Generate Invoice
       │
       ▼
Invoice Created
       │
       ▼
Track Payment
       │
       ▼
Invoice Completed
```

The system should check that the invoice number does not already exist before inserting a new invoice.

---

# 💰 Payment Management

Invoices can be monitored based on their payment status.

For example:

```text
Total Amount
     │
     ├── Amount Paid
     │
     └── Outstanding Amount
```

The outstanding amount is calculated as:

```text
Outstanding Amount = Total Amount - Amount Paid
```

Possible invoice statuses include:

```text
Pending
In Progress
Partially Paid
Paid
Completed
Cancelled
```

The exact status values should correspond to the application's database configuration.

---

# 📅 Job Calendar

The Job Calendar allows users to manage scheduled work.

A job may contain information such as:

```text
Customer
Invoice Number
Job Description
Scheduled Date
Start Time
End Time
Location
Status
Notes
```

The calendar can be used to coordinate jobs and provide users with an overview of upcoming work.

---

# 🔗 Google Apps Script Integration

The application can communicate with Google Apps Script to perform operations that are better handled by Google's services.

Possible operations include:

- Generating quotation documents
- Generating invoice documents
- Creating PDFs
- Updating Google Drive files
- Managing document templates
- Updating Supabase-related business information through an API bridge

The application should display an appropriate loading/waiting state while a Google Apps Script request is being processed.

Example workflow:

```text
Streamlit
    │
    ▼
Google Apps Script API
    │
    ├── Generate Document
    ├── Generate PDF
    └── Store in Google Drive
             │
             ▼
        Return Document URL
             │
             ▼
          Streamlit
```

---

# 🚀 Deployment

The application is designed to support low-cost cloud deployment.

Potential deployment environments include:

- Streamlit Community Cloud
- Other Python/Streamlit hosting platforms
- Self-hosted environments
- Cloud virtual machines

Before deployment, configure the required environment variables securely.

Do not upload `.env` files or private credentials to GitHub.

---

# 🧪 Testing

Before deploying a new version, test the following workflows:

### Authentication

- [ ] User can log in
- [ ] Invalid credentials are rejected
- [ ] User roles are correctly identified
- [ ] Unauthorized functionality is restricted

### Quotations

- [ ] Create quotation
- [ ] Edit quotation
- [ ] Delete quotation
- [ ] Calculate totals
- [ ] Calculate tax
- [ ] Calculate deposit
- [ ] Generate quotation document
- [ ] Generate quotation PDF

### Invoices

- [ ] Generate invoice
- [ ] Prevent duplicate invoice numbers
- [ ] Calculate invoice totals
- [ ] Record payments
- [ ] Calculate outstanding amount
- [ ] Update invoice status
- [ ] Generate invoice document

### Job Calendar

- [ ] Create job
- [ ] Edit job
- [ ] Delete job
- [ ] View scheduled jobs

### Database

- [ ] Supabase connection works
- [ ] Insert operations work
- [ ] Update operations work
- [ ] Delete operations work
- [ ] Database errors are handled gracefully

---

# 🐛 Troubleshooting

## Supabase Connection Error

Check that the environment variables are correctly configured:

```text
SUPABASE_URL
SUPABASE_KEY
```

Also verify that the Supabase project is running and accessible.

---

## `supabase_url is required`

This normally indicates that the application did not receive the Supabase URL.

Check your `.env` or Streamlit secrets configuration.

---

## `Email not confirmed`

If Supabase authentication reports:

```text
Email not confirmed
```

verify the user's email through Supabase Authentication or configure the project's email-confirmation settings appropriately for the intended environment.

---

## Database Schema Errors

Errors such as:

```text
column "inv_status" does not exist
```

indicate that the application code and database schema are not synchronized.

Verify that:

1. The database contains the required column.
2. The application uses the correct column name.
3. Supabase's schema cache is up to date.
4. The query references the correct table.

---

# 🔄 Development Workflow

The recommended development workflow is:

```text
Create Feature
     │
     ▼
Develop Locally
     │
     ▼
Test
     │
     ▼
Commit Changes
     │
     ▼
Push to GitHub
     │
     ▼
Deploy
     │
     ▼
Monitor
```

Example Git commands:

```bash
git status

git add .

git commit -m "Add quotation management improvements"

git push origin main
```

---

# 📌 Future Improvements

Potential future enhancements include:

- Dashboard with financial statistics
- Advanced reporting
- Customer management module
- Automated payment reminders
- Emailing invoices directly to customers
- Automated quotation expiry notifications
- Improved role-based permissions
- Audit logging
- Advanced search and filtering
- Mobile-responsive interface
- Automated database backups
- Improved document templates
- Payment gateway integration
- Customer portal
- Sales and revenue analytics

---

# 🤝 Contributing

Contributions and suggestions are welcome.

To contribute:

1. Fork the repository.
2. Create a feature branch.

```bash
git checkout -b feature/new-feature
```

3. Make your changes.
4. Test the application.
5. Commit your changes.

```bash
git commit -m "Add new feature"
```

6. Push the branch.

```bash
git push origin feature/new-feature
```

7. Create a Pull Request.

---

# 📄 License

This project is proprietary software developed for **Absaluminum**.

Unless otherwise specified, the source code, database structure, business logic, documents, and associated assets may not be copied, redistributed, or used commercially without permission from the project owner.

---

# 👨‍💻 Project

**Absaluminum Invoicing and Quotations System**

Built with:

**Python · Streamlit · Supabase · PostgreSQL · Google Apps Script · Google Drive**

---

## ⭐ Project Status

**Status:** Active Development

The application is continuously being improved with new features, performance optimizations, database improvements, and business-process automation.