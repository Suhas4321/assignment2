"""Seed the database with sample HCPs and interactions for demo purposes."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import SessionLocal, engine
from db.models import Base, FollowUp, HCP, Interaction


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    if db.query(HCP).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    # Sample HCPs
    hcps_data = [
        {"name": "Dr. Priya Sharma", "specialty": "Cardiologist", "hospital": "Apollo Hospital", "location": "Mumbai", "email": "priya.sharma@apollo.com", "phone": "+91-98200-11111"},
        {"name": "Dr. Rajesh Kumar", "specialty": "Oncologist", "hospital": "Fortis Healthcare", "location": "Delhi", "email": "rajesh.kumar@fortis.com", "phone": "+91-98200-22222"},
        {"name": "Dr. Anita Patel", "specialty": "Neurologist", "hospital": "Kokilaben Hospital", "location": "Mumbai", "email": "anita.patel@kokilaben.com", "phone": "+91-98200-33333"},
        {"name": "Dr. Suresh Menon", "specialty": "Diabetologist", "hospital": "Max Healthcare", "location": "Bangalore", "email": "suresh.menon@max.com", "phone": "+91-98200-44444"},
        {"name": "Dr. Kavitha Rao", "specialty": "Pulmonologist", "hospital": "Narayana Health", "location": "Hyderabad", "email": "kavitha.rao@narayana.com", "phone": "+91-98200-55555"},
        {"name": "Dr. Amit Verma", "specialty": "Gastroenterologist", "hospital": "Medanta", "location": "Gurugram", "email": "amit.verma@medanta.com", "phone": "+91-98200-66666"},
        {"name": "Dr. Deepa Nair", "specialty": "Rheumatologist", "hospital": "Christian Medical College", "location": "Vellore", "email": "deepa.nair@cmc.com", "phone": "+91-98200-77777"},
        {"name": "Dr. Vikram Singh", "specialty": "Endocrinologist", "hospital": "AIIMS", "location": "Delhi", "email": "vikram.singh@aiims.com", "phone": "+91-98200-88888"},
        {"name": "Dr. Meena Iyer", "specialty": "Nephrologist", "hospital": "Manipal Hospital", "location": "Bangalore", "email": "meena.iyer@manipal.com", "phone": "+91-98200-99999"},
        {"name": "Dr. Arun Chopra", "specialty": "Cardiologist", "hospital": "Lilavati Hospital", "location": "Mumbai", "email": "arun.chopra@lilavati.com", "phone": "+91-98200-10101"},
        {"name": "Dr. Sunita Reddy", "specialty": "Hematologist", "hospital": "Yashoda Hospital", "location": "Hyderabad", "email": "sunita.reddy@yashoda.com", "phone": "+91-98200-20202"},
        {"name": "Dr. Ravi Desai", "specialty": "Oncologist", "hospital": "Tata Memorial", "location": "Mumbai", "email": "ravi.desai@tata.com", "phone": "+91-98200-30303"},
    ]

    hcp_objects = []
    for data in hcps_data:
        hcp = HCP(**data)
        db.add(hcp)
        hcp_objects.append(hcp)

    db.commit()
    for h in hcp_objects:
        db.refresh(h)

    # Sample Interactions
    interactions_data = [
        {
            "hcp_id": hcp_objects[0].id,
            "rep_id": "field_rep_001",
            "interaction_type": "Meeting",
            "date": "2025-04-15",
            "time": "10:30",
            "attendees": "Dr. Priya Sharma, Rep John Doe",
            "topics_discussed": "CardioMax 10mg efficacy, clinical trial results, dosage optimization",
            "materials_shared": ["CardioMax brochure", "Phase III trial summary"],
            "samples_distributed": ["CardioMax 10mg x5"],
            "sentiment": "Positive",
            "outcomes": "Dr. Sharma showed strong interest in CardioMax. Agreed to prescribe for next 3 patients.",
            "follow_up_actions": "Send full clinical trial data by email within 2 days",
            "ai_summary": "Productive meeting with Dr. Priya Sharma at Apollo. She expressed enthusiasm for CardioMax 10mg efficacy data and agreed to trial it on her next 3 eligible patients.",
            "ai_suggested_followups": ["Send Phase III data PDF", "Schedule follow-up in 2 weeks", "Invite to upcoming CME event"],
        },
        {
            "hcp_id": hcp_objects[1].id,
            "rep_id": "field_rep_001",
            "interaction_type": "Phone Call",
            "date": "2025-04-10",
            "time": "14:00",
            "attendees": "Dr. Rajesh Kumar",
            "topics_discussed": "OncoBest dosage protocol, patient eligibility criteria",
            "materials_shared": [],
            "samples_distributed": [],
            "sentiment": "Neutral",
            "outcomes": "Dr. Kumar requested more information on patient eligibility for OncoBest.",
            "follow_up_actions": "Send eligibility criteria document and schedule an in-person meeting",
            "ai_summary": "Brief phone call with Dr. Rajesh Kumar. He is evaluating OncoBest for select patients but needs detailed eligibility criteria before prescribing.",
            "ai_suggested_followups": ["Email eligibility criteria", "Book in-person meeting", "Share patient case studies"],
        },
        {
            "hcp_id": hcp_objects[2].id,
            "rep_id": "field_rep_001",
            "interaction_type": "Virtual Meeting",
            "date": "2025-04-08",
            "time": "16:00",
            "attendees": "Dr. Anita Patel, Clinical Coordinator",
            "topics_discussed": "NeuroPlus for migraine management, side effect profile",
            "materials_shared": ["NeuroPlus brochure", "Safety data sheet"],
            "samples_distributed": ["NeuroPlus 5mg x10"],
            "sentiment": "Positive",
            "outcomes": "Very receptive. Will incorporate NeuroPlus into treatment protocol for chronic migraine patients.",
            "follow_up_actions": "Follow up in 1 month to review patient outcomes",
            "ai_summary": "Excellent virtual meeting with Dr. Anita Patel. Demonstrated NeuroPlus efficacy in chronic migraine. She plans to start 10 patients immediately.",
            "ai_suggested_followups": ["Monthly outcome review call", "Send outcome tracking template", "Invite to neurology symposium"],
        },
    ]

    for data in interactions_data:
        interaction = Interaction(**data)
        db.add(interaction)

    db.commit()

    # Sample Follow-ups
    followups_data = [
        {
            "hcp_id": hcp_objects[0].id,
            "scheduled_date": "2025-04-29",
            "notes": "Follow up on CardioMax prescriptions and collect initial patient feedback",
            "priority": "high",
            "status": "pending",
        },
        {
            "hcp_id": hcp_objects[1].id,
            "scheduled_date": "2025-04-22",
            "notes": "Send OncoBest eligibility criteria and schedule in-person demo",
            "priority": "medium",
            "status": "pending",
        },
    ]

    for data in followups_data:
        followup = FollowUp(**data)
        db.add(followup)

    db.commit()
    db.close()

    print(f"✅ Database seeded successfully:")
    print(f"   - {len(hcps_data)} HCPs created")
    print(f"   - {len(interactions_data)} Interactions created")
    print(f"   - {len(followups_data)} Follow-ups created")


if __name__ == "__main__":
    seed()
