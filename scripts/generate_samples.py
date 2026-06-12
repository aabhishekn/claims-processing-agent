"""Generate 5 dummy FNOL sample documents (3 PDFs + 2 TXTs) into samples/.

Each sample is designed to exercise one routing outcome:
  fnol_01_fasttrack.txt       -> Fast-track          (damage 18,000, complete)
  fnol_02_missing_fields.txt  -> Manual Review       (no policy number / damage estimate)
  fnol_03_fraud_flag.pdf      -> Investigation Flag  (description contains "staged")
  fnol_04_injury.pdf          -> Specialist Queue    (claim type: Injury)
  fnol_05_high_damage.pdf     -> Standard Processing (damage 350,000, complete)
"""

from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

FNOL_01 = """\
FIRST NOTICE OF LOSS (FNOL) - AUTOMOBILE
Reported via: Customer Portal

Policy Number: POL-2026-88341
Policyholder Name: Rajesh Kumar Sharma
Effective Dates: 2026-01-01 to 2026-12-31

Incident Date: 2026-06-02
Incident Time: 08:45 AM
Location: Andheri East, Mumbai, Maharashtra
Description: While reversing out of the office parking lot, the insured vehicle scraped against a concrete pillar, causing scratches and a dent on the rear left door panel.

Claimant: Rajesh Kumar Sharma
Third Parties: None
Contact Details: +91 98200 11223, rajesh.sharma@example.com

Asset Type: Private Car - Hyundai Creta 2023
Asset ID: MH02-AB-4455 / VIN MALC381CLNM123456
Estimated Damage: Rs. 18,000

Claim Type: Own Damage
Attachments: photos_rear_door.zip, parking_cctv.mp4
Initial Estimate: Rs. 17,500
"""

FNOL_02 = """\
FIRST NOTICE OF LOSS (FNOL) - AUTOMOBILE
Reported via: Call Centre (transcribed)

Policy Number:
Policyholder Name: Meera Iyer
Effective Dates: 2026-03-15 to 2027-03-14

Incident Date: 2026-06-08
Incident Time:
Location: Outer Ring Road, Bengaluru, Karnataka
Description: Caller reports her car was hit by an unidentified two-wheeler while parked outside her residence. Front bumper cracked. Caller did not have her policy documents on hand during the call.

Claimant: Meera Iyer
Third Parties: Unknown two-wheeler rider (hit and run)
Contact Details: +91 99450 33877

Asset Type: Private Car - Maruti Baleno 2022
Asset ID:
Estimated Damage:

Claim Type: Own Damage
Attachments: None
Initial Estimate:
"""

FNOL_03 = """\
FIRST NOTICE OF LOSS (FNOL) - AUTOMOBILE
Reported via: Agent Email

Policy Number: POL-2026-10277
Policyholder Name: Vikram Singh Rathore
Effective Dates: 2026-02-01 to 2027-01-31

Incident Date: 2026-06-05
Incident Time: 11:30 PM
Location: NH-48 Service Road, Gurugram, Haryana
Description: Insured claims the vehicle was rear-ended at night by a truck that fled the scene. However, the damage pattern on the front axle appears inconsistent with a rear-end collision, and a witness suggested the accident may have been staged to claim insurance.

Claimant: Vikram Singh Rathore
Third Parties: Unidentified truck (alleged)
Contact Details: +91 98111 90422, vikram.rathore@example.com

Asset Type: Private Car - Toyota Fortuner 2021
Asset ID: HR26-CX-7788 / VIN MBJ11JV4007654321
Estimated Damage: Rs. 2,80,000

Claim Type: Own Damage
Attachments: damage_photos.zip, fir_copy.pdf
Initial Estimate: Rs. 2,60,000
"""

FNOL_04 = """\
FIRST NOTICE OF LOSS (FNOL) - AUTOMOBILE
Reported via: Mobile App

Policy Number: POL-2026-55610
Policyholder Name: Ananya Deshpande
Effective Dates: 2026-04-01 to 2027-03-31

Incident Date: 2026-06-10
Incident Time: 06:15 PM
Location: FC Road, Pune, Maharashtra
Description: The insured vehicle collided with a motorcycle at a junction. The motorcycle rider sustained a fractured arm and was taken to Ruby Hall Clinic. Vehicle has front bumper and headlamp damage.

Claimant: Ananya Deshpande
Third Parties: Motorcycle rider - Suresh Pawar (injured)
Contact Details: +91 98600 45901, ananya.d@example.com

Asset Type: Private Car - Tata Nexon EV 2024
Asset ID: MH12-QR-2210 / VIN MAT62534PLA098765
Estimated Damage: Rs. 95,000

Claim Type: Injury
Attachments: accident_photos.zip, hospital_admission.pdf, police_report.pdf
Initial Estimate: Rs. 90,000
"""

FNOL_05 = """\
FIRST NOTICE OF LOSS (FNOL) - AUTOMOBILE
Reported via: Branch Walk-in

Policy Number: POL-2026-73922
Policyholder Name: Arjun Nair
Effective Dates: 2026-01-20 to 2027-01-19

Incident Date: 2026-06-11
Incident Time: 02:30 AM
Location: East Coast Road, Chennai, Tamil Nadu
Description: During heavy overnight rain, a roadside tree fell on the insured vehicle which was parked under it. The roof, windshield, and bonnet are crushed. No persons were harmed.

Claimant: Arjun Nair
Third Parties: None
Contact Details: +91 98410 77665, arjun.nair@example.com

Asset Type: Private Car - Honda City 2023
Asset ID: TN07-DZ-9914 / VIN MRHGM6648NP445566
Estimated Damage: Rs. 3,50,000

Claim Type: Own Damage
Attachments: tree_damage_photos.zip, weather_report.pdf
Initial Estimate: Rs. 3,40,000
"""

TXT_SAMPLES = {
    "fnol_01_fasttrack.txt": FNOL_01,
    "fnol_02_missing_fields.txt": FNOL_02,
}

PDF_SAMPLES = {
    "fnol_03_fraud_flag.pdf": FNOL_03,
    "fnol_04_injury.pdf": FNOL_04,
    "fnol_05_high_damage.pdf": FNOL_05,
}


def write_pdf(path: Path, content: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin
    for line in content.splitlines():
        # naive wrap for long description lines
        chunks = [line[i : i + 95] for i in range(0, max(len(line), 1), 95)]
        for chunk in chunks:
            if y < margin:
                c.showPage()
                y = height - margin
            font = "Helvetica-Bold" if chunk.isupper() or chunk.startswith("FIRST NOTICE") else "Helvetica"
            c.setFont(font, 9)
            c.drawString(margin, y, chunk)
            y -= 5 * mm
    c.save()


def main() -> None:
    SAMPLES_DIR.mkdir(exist_ok=True)
    for name, content in TXT_SAMPLES.items():
        (SAMPLES_DIR / name).write_text(content, encoding="utf-8")
        print(f"wrote {SAMPLES_DIR / name}")
    for name, content in PDF_SAMPLES.items():
        write_pdf(SAMPLES_DIR / name, content)
        print(f"wrote {SAMPLES_DIR / name}")


if __name__ == "__main__":
    main()
