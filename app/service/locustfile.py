import uuid
from locust import HttpUser, task, between


class Analyst(HttpUser):
    wait_time = between(1, 3)

    @task
    def submit_and_poll(self):
        alert = (
            f"LT-{uuid.uuid4().hex[:8]}"  # unique, so idempotency doesn't hide the load
        )
        r = self.client.post(
            "/cases",
            json={
                "alert_id": alert,
                "alert_text": f"Alert {alert}: three cash deposits in 7 days.",
            },
        )
        self.client.get(f"/cases/{r.json()['case_id']}", name="/cases/[id]")
