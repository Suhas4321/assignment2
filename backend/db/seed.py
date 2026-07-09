"""Seed sample HCP data for a realistic demo."""
from sqlalchemy.orm import Session
from db import models

SAMPLE_HCPS = [
    {
        "name": "Dr. Sarah Chen",
        "specialty": "Oncology",
        "hospital": "Memorial Sloan Kettering",
        "location": "New York, NY",
        "email": "s.chen@mskcc.org",
        "phone": "+1-212-555-0101",
    },
    {
        "name": "Dr. Rajesh Sharma",
        "specialty": "Cardiology",
        "hospital": "Apollo Hospitals",
        "location": "Mumbai, India",
        "email": "r.sharma@apollohospitals.com",
        "phone": "+91-22-5555-0202",
    },
    {
        "name": "Dr. Emily Watson",
        "specialty": "Endocrinology",
        "hospital": "Mayo Clinic",
        "location": "Rochester, MN",
        "email": "e.watson@mayo.edu",
        "phone": "+1-507-555-0303",
    },
    {
        "name": "Dr. Michael Torres",
        "specialty": "Neurology",
        "hospital": "Cleveland Clinic",
        "location": "Cleveland, OH",
        "email": "m.torres@ccf.org",
        "phone": "+1-216-555-0404",
    },
    {
        "name": "Dr. Priya Patel",
        "specialty": "Oncology",
        "hospital": "Tata Memorial Hospital",
        "location": "Mumbai, India",
        "email": "p.patel@tmc.gov.in",
        "phone": "+91-22-5555-0505",
    },
    {
        "name": "Dr. James Okonkwo",
        "specialty": "Infectious Disease",
        "hospital": "Johns Hopkins Hospital",
        "location": "Baltimore, MD",
        "email": "j.okonkwo@jhmi.edu",
        "phone": "+1-410-555-0606",
    },
    {
        "name": "Dr. Lisa Bergmann",
        "specialty": "Rheumatology",
        "hospital": "Charité – Universitätsmedizin",
        "location": "Berlin, Germany",
        "email": "l.bergmann@charite.de",
        "phone": "+49-30-555-0707",
    },
    {
        "name": "Dr. Ananya Krishnan",
        "specialty": "Pulmonology",
        "hospital": "AIIMS",
        "location": "New Delhi, India",
        "email": "a.krishnan@aiims.edu",
        "phone": "+91-11-5555-0808",
    },
    {
        "name": "Dr. Robert Kim",
        "specialty": "Cardiology",
        "hospital": "Stanford Health Care",
        "location": "Palo Alto, CA",
        "email": "r.kim@stanford.edu",
        "phone": "+1-650-555-0909",
    },
    {
        "name": "Dr. Fatima Al-Hassan",
        "specialty": "Dermatology",
        "hospital": "King Faisal Specialist Hospital",
        "location": "Riyadh, Saudi Arabia",
        "email": "f.alhassan@kfshrc.edu.sa",
        "phone": "+966-11-555-1010",
    },
    {
        "name": "Dr. Thomas Wright",
        "specialty": "Orthopedics",
        "hospital": "Hospital for Special Surgery",
        "location": "New York, NY",
        "email": "t.wright@hss.edu",
        "phone": "+1-212-555-1111",
    },
    {
        "name": "Dr. Meera Nair",
        "specialty": "Pediatrics",
        "hospital": "Rainbow Children's Hospital",
        "location": "Hyderabad, India",
        "email": "m.nair@rainbowhospitals.in",
        "phone": "+91-40-5555-1212",
    },
    {
        "name": "Dr. Carlos Mendoza",
        "specialty": "Gastroenterology",
        "hospital": "Cedars-Sinai Medical Center",
        "location": "Los Angeles, CA",
        "email": "c.mendoza@cshs.org",
        "phone": "+1-310-555-1313",
    },
    {
        "name": "Dr. Hannah Okafor",
        "specialty": "Hematology",
        "hospital": "MD Anderson Cancer Center",
        "location": "Houston, TX",
        "email": "h.okafor@mdanderson.org",
        "phone": "+1-713-555-1414",
    },
    {
        "name": "Dr. Vikram Singh",
        "specialty": "Nephrology",
        "hospital": "Fortis Escorts",
        "location": "Delhi, India",
        "email": "v.singh@fortishealthcare.com",
        "phone": "+91-11-5555-1515",
    },
]


def seed_database(db: Session) -> int:
    """Insert sample HCPs if the table is empty. Returns count inserted."""
    existing = db.query(models.HCP).count()
    if existing > 0:
        return 0
    for row in SAMPLE_HCPS:
        db.add(models.HCP(**row))
    db.commit()
    return len(SAMPLE_HCPS)
