"""Load test for the Red Tape Navigator API (Locust).

Run (against a local server started with relaxed rate limits):
  RATE_LIMIT_PER_MINUTE=100000 AUTH_RATE_LIMIT_PER_MINUTE=100000 uvicorn app.main:app --port 8000
  locust -f scripts/loadtest/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s --csv loadtest
Each virtual user: register -> consent -> goal -> research -> checklist -> answer interview questions -> review payload.
"""
import uuid

from locust import HttpUser, between, task

ANSWERS = {
    "applicant_name": "Asha Roy", "father_name": "Ravi Roy", "mobile": "9876543210", "email": "asha@example.com",
    "residence_address": "12 Park Street", "residence_pincode": "700016", "business_name": "Sweet Crumbs",
    "food_products": "Bread", "annual_turnover": "900000", "premises_address": "5 College St",
    "premises_pincode": "700073", "premises_ownership": "rented", "num_employees": "3", "premises_area_sqft": "350",
    "date_of_commencement": "01/01/2027", "organisation_type": "proprietorship",
    "dob": "14/03/1990", "gender": "female", "social_category": "general", "investment_amount": "400000",
    "bank_ifsc": "SBIN0001234", "bank_account_number": "123456789012", "pan": "ABCPE1234F", "aadhaar": "210000000007",
}


class Citizen(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        creds = {"email": f"load-{uuid.uuid4().hex[:12]}@example.com", "password": "Load-test-" + uuid.uuid4().hex}
        r = self.client.post("/auth/register", json=creds, name="POST /auth/register")
        self.h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        self.client.post("/consent", json={"purpose": "service", "granted": True}, headers=self.h, name="POST /consent")
        s = self.client.post("/sessions", json={"goal": "I want to open a small bakery in Kolkata", "language": "en"},
                             headers=self.h, name="POST /sessions").json()
        self.sid = s["id"]
        self.client.post(f"/sessions/{self.sid}/research", json={}, headers=self.h, name="POST /sessions/{id}/research")

    @task(3)
    def interview(self):
        st = self.client.get(f"/sessions/{self.sid}/interview", headers=self.h, name="GET /sessions/{id}/interview").json()
        qs = st.get("questions", [])
        if qs:
            self.client.post(f"/sessions/{self.sid}/interview", json={"answers": {q["key"]: ANSWERS[q["key"]] for q in qs}},
                             headers=self.h, name="POST /sessions/{id}/interview")

    @task(2)
    def checklist(self):
        self.client.get(f"/sessions/{self.sid}/checklist", headers=self.h, name="GET /sessions/{id}/checklist")

    @task(1)
    def review(self):
        self.client.get(f"/sessions/{self.sid}/review", headers=self.h, name="GET /sessions/{id}/review (fills 3 PDFs)")

    @task(1)
    def health(self):
        self.client.get("/health", name="GET /health")
