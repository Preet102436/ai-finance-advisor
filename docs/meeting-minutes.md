# Meeting Minutes

## Meeting Date 16 Aug 2026
**Attendees:** Parth Patel, Preetkumar Navinbhai Patel, Thiwanka Kaushalya Nagasanga
**Team leader this period: Preet Patel**

**Discussed:**
- Reviewed the overall progress of the **AI-Powered Personal Finance Advisor** project and compared the current development status with the project proposal and delivery roadmap.

- Discussed the requirements for **Assessment 2 Part 1**, particularly the need for each team member to provide clear evidence of their individual contribution to the project.

- Reviewed the team's **Trello board** to check completed, in-progress, and upcoming tasks for each subsystem.
- Parth provided an update on the **Budgeting and Forecasting subsystem**. The requirements and scope for this subsystem have been confirmed, while prototype development and further testing are continuing.
- Discussed the current forecasting approach. The subsystem uses transaction information to generate budget recommendations and future cash-flow forecasts.
- Discussed the use of a **weighted average of the previous three months' category spending** for generating budget recommendations.

- Discussed anomaly detection and the automated tests added to verify the anomaly-detection functionality.

- Reviewed the process of merging individual subsystem work into the shared GitHub repository using pull requests.

- Discussed the remaining work for the Budgeting and Forecasting subsystem, particularly integration with real transaction data from the Expense Tracking subsystem.

- Discussed the need to test the forecasting model with a larger transaction dataset and adjust the anomaly-detection threshold if required.

- Preetkumar provided an update on the **Expense Tracking and OCR subsystem**, including work related to transaction handling, receipt processing, and preparation of data required by other subsystems.

- Thiwanka provided an update on the **Chatbot and Savings Recommendation subsystem** and discussed its future integration with financial and transaction data.

- Discussed dependencies between the three subsystems. In particular, the Budgeting and Forecasting subsystem will require transaction data from the Expense Tracking subsystem for complete integration and testing.

- Discussed technical documentation and agreed that documentation should be updated alongside development rather than being completed only at the end of the project.
- Reviewed current time management and discussed breaking larger development tasks into smaller Trello tasks so that delays can be identified earlier.
- Discussed preparation for future subsystem integration and agreed that individual components should be properly tested before integration.

**Decisions:**

- Continue using separate GitHub branches for individual subsystem development.

- All team members will use meaningful and identifiable GitHub commits to provide evidence of their individual contributions.

- Pull requests will be used when merging individual subsystem work into the main branch.

- Trello will continue to be used to monitor project tasks and individual progress.

- The Budgeting and Forecasting subsystem will continue using the current forecasting approach with Prophet and a moving-average fallback.

- Automated testing will continue to be added for important functions, particularly forecasting and anomaly detection.

- Larger Trello tasks will be divided into smaller tasks to improve progress tracking and time management.

- Technical documentation will be updated during development rather than waiting until the end of the project.

- Each team member will continue developing and testing their assigned subsystem before full system integration.

- The team will prepare the subsystems so that integration can be carried out according to the project roadmap.



## Meeting Date :  12 August 2026
**Attendees:** Parth Patel, Preetkumar Navinbhai Patel, Thiwanka Kaushalya Nagasanga
**Team leader this period: Preet Patel**

**Discussed:**
- Reviewed the Week 5 Workshop Activities and discussed the design requirements for the AI-Powered Personal Finance Advisor.
- Discussed the main classes required from the Level 1 use cases, including User, Expense, Category, Receipt, Budget, BudgetRecommendation, SpendingInsight, SavingsGoal, SavingsRecommendation, Transaction, AnomalyAlert, Forecast, ChatSession, and ChatMessage.
- Reviewed the UML class diagrams and discussed how the classes are connected with each team member's assigned subsystem.
- Discussed the required user inputs and UI components for expense tracking, receipt scanning, budgeting, savings recommendations, forecasting, and the financial chatbot.
- Reviewed the proposed interfaces, including Login/Register, Dashboard, Expense Tracker, Receipt Scanner, Budget Suggestion, Spending Insight, Savings Suggestions, Cash Flow Forecast, Anomaly Alerts, and Financial Chatbot.
- Discussed the PostgreSQL database design and ERD, including entities, primary keys, foreign keys, and relationships.
- Discussed client-server communication using HTTPS REST APIs between the frontend, backend modules, PostgreSQL database, and AI services.
- Reviewed the current development progress of each team member and checked progress against the project roadmap.
- Parth provided an update on the Budgeting and Forecasting subsystem, including the budgeting/forecasting prototype, Prophet forecasting, moving-average fallback, and anomaly-detection testing.
- Reviewed GitHub branches, commits, and pull requests to track individual contributions.
- Reviewed Trello tasks and discussed completed, in-progress, and upcoming work.
- Discussed the next development tasks for the Expense Tracking/OCR, Budgeting/Forecasting, and Chatbot/Savings subsystems.

**Decisions:**
- Continue using separate GitHub branches for each team member's subsystem.
- Continue using Trello to monitor individual tasks and overall project progress.
- Use PostgreSQL as the project database.
- Use HTTPS REST APIs for communication between the frontend and backend.
- Continue developing each subsystem separately before integration.
- Keep UML diagrams, ERD, UI designs, and technical documentation updated as development progresses.
- Follow the project roadmap and prepare the individual subsystems for later integration and testing.



**Action items:**
| Task | Owner | Due |
|---|---|---|
| Continue Budgeting and Forecasting prototype development and testing | Parth Patel | Week 6 |
| Continue Expense Tracking and OCR subsystem development | Preetkumar Navinbhai Patel | Week 6 |
| Continue Chatbot and Savings Recommendation subsystem development | Thiwanka Kaushalya Nagasanga | Week 7-8 |
| Review and update UML class diagrams for individual use cases | All Members | Week 5-6 |
| Review database entities and ERD | All Members | Week 6 |
| Update individual GitHub branches with meaningful commits | All Members | Ongoing |
| Update Trello cards according to current project progress | All Members | Ongoing |
| Prepare subsystems for future integration | All Members | Before Week 9 |

---


