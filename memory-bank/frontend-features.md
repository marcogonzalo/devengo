# Frontend Functionalities Overview

## Introduction

This document describes the main frontend functionalities of the Devengo project, focusing on user experience, business requirements, and integration with the accrual processing backend. The frontend is designed to provide a seamless, secure, and informative interface for managing client data and monitoring accruals.

The frontend must be a responsive React dashboard for the Devengo project with components for admin's email-only login, client external IDs management, accrual year overview, visual accrual reports, and report downloads. Include light/dark mode toggle, error notifications, and ensure all data operations integrate with the backend API

---

## 1. Authentication

- **Email-Only Login (Passwordless Authentication):**
  - Users log in by entering their email address.
  - The system sends a magic link (URL) to the provided email.
  - Clicking the link authenticates the user without requiring a password.
  - This approach enhances security and user convenience.

---

## 2. Client External ID Management

- **View and Edit Client External IDs:**
  - Users can search for and select a client.
  - The interface displays all known external IDs (e.g., CRM, invoicing system) associated with the client.
  - Users can add, edit, or remove external IDs as needed.

- **Identify and Resolve Missing External IDs:**
  - The application highlights clients with missing or incomplete external IDs, indicating which systems are missing.
  - Users are prompted to provide missing information, ensuring data consistency across systems.
  - Bulk actions and filters are available to streamline the resolution process.

---

## 3. Accrual Year Overview

- **Available Years:**
  - Users can view a list of years for which accrual data is available.

- **Yearly Accrual Summary:**
  - For each year, the following metrics are displayed:
    - Total number of contracts
    - Total contract amount
    - Amount accrued in the year
    - Amount pending to accrue for the same year
  - Data is presented in a clear, concise dashboard format.

---

## 4. Visual Accrual Reports

- **Yearly and Monthly Breakdown:**
  - Users can select a year to view detailed accrual activity.
  - The report includes:
    - Contracts with accruals in the selected period (completed or not)
    - Month-by-month accrual progress
    - Contracts pending to be accrued
  - Interactive charts and tables provide visual insights into accrual distribution and outstanding amounts.

- **Filtering and Drill-Down:**
  - Users can filter by contract status, client, or other relevant criteria.
  - Clicking on a contract or month reveals more detailed information.

---

## 5. Accrual Report Download

- **Custom Date Range Export:**
  - Users can specify a custom date range for accrual reporting.
  - The system generates a downloadable report (e.g., CSV, Excel, or PDF) containing all relevant accrual data for the selected period.
  - The report includes contract details, amounts, statuses, and summary statistics.

---

## 6. User Experience and Accessibility

- **Light and Dark Mode:**
  - The frontend supports both light and dark themes, with dark mode as the default.

- **Responsive Design:**
  - The interface is fully responsive and works across desktops, tablets, and mobile devices.

- **Notifications and Error Handling:**
  - Users receive clear feedback for actions (e.g., successful updates, errors, missing data).

---

## 7. Security and Privacy

- **Secure Authentication:**
  - All authentication and data access follow best security practices.
  - Sensitive operations are protected and logged.

- **Data Privacy:**
  - User and client data is handled in compliance with privacy regulations.

---

## 8. Integration with Backend

- The frontend communicates with the backend API for all data operations, including:
  - Authentication (magic link flow)
  - Fetching and updating client external IDs
  - Retrieving accrual summaries and reports
  - Downloading accrual data

---

## 9. Future Enhancements

- **Batch Actions:**
  - Bulk editing and reporting for large client lists.
- **Advanced Filtering:**
  - More granular filters for reports and client management.
- **Customizable Dashboards:**
  - User-configurable widgets and views.

---

This document provides a high-level overview of the frontend features. For technical implementation details, refer to the frontend codebase and API documentation. 