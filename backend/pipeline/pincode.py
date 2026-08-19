"""
Indian Pincode Lookup — pincode to city/state/district mapping.

Uses India Post API (free, no key needed) for pincode lookups.
"""

import json
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List


class PincodeService:
    """Lookup Indian pincodes and format addresses."""

    # Common Indian state abbreviations to full names
    STATE_MAP = {
        "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam",
        "BR": "Bihar", "CG": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat",
        "HR": "Haryana", "HP": "Himachal Pradesh", "JH": "Jharkhand",
        "KA": "Karnataka", "KL": "Kerala", "MP": "Madhya Pradesh",
        "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya",
        "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab",
        "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu",
        "TS": "Telangana", "TR": "Tripura", "UP": "Uttar Pradesh",
        "UK": "Uttarakhand", "WB": "West Bengal",
        "AN": "Andaman & Nicobar", "CH": "Chandigarh", "DD": "Dadra & Nagar Haveli",
        "DL": "Delhi", "JK": "Jammu & Kashmir", "LA": "Ladakh",
        "LD": "Lakshadweep", "PY": "Puducherry",
    }

    def lookup(self, pincode: str) -> Dict[str, Any]:
        """Look up a pincode and return location details."""
        pincode = pincode.strip()
        if not pincode or not pincode.isdigit() or len(pincode) != 6:
            return {"error": "Invalid pincode. Must be 6 digits."}

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = f"https://api.postalpincode.in/pincode/{pincode}"
            req = urllib.request.Request(url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data or data[0].get("Status") != "Success":
                return {"error": f"Pincode {pincode} not found."}

            post_offices = data[0].get("PostOffice", [])
            if not post_offices:
                return {"error": f"No post offices found for pincode {pincode}."}

            first = post_offices[0]
            result = {
                "pincode": pincode,
                "district": first.get("District", ""),
                "state": first.get("State", ""),
                "country": first.get("Country", "India"),
                "region": first.get("Region", ""),
                "division": first.get("Division", ""),
                "circle": first.get("Circle", ""),
                "post_offices": [po.get("Name", "") for po in post_offices[:10]],
                "total_post_offices": len(post_offices),
            }

            # Format Indian address
            result["formatted_address"] = (
                f"{first.get('District', '')}, {first.get('State', '')} - {pincode}"
            )

            return result

        except urllib.error.URLError as e:
            return {"error": f"API error: {e}"}
        except Exception as e:
            return {"error": f"Lookup error: {e}"}

    def format_address(self, pincode: str, landmark: str = "", street: str = "") -> str:
        """Format a complete Indian address."""
        result = self.lookup(pincode)
        if result.get("error"):
            return result["error"]

        parts = []
        if street:
            parts.append(street)
        if landmark:
            parts.append(landmark)
        parts.append(result.get("district", ""))
        parts.append(result.get("state", ""))
        parts.append(f"PIN: {pincode}")
        parts.append("India")

        return ", ".join(parts)

    def validate_phone(self, phone: str) -> Dict[str, Any]:
        """Validate Indian phone number format."""
        phone = phone.strip().replace(" ", "").replace("-", "")

        # Remove country code
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) == 12:
            phone = phone[2:]

        # Validate
        if not phone.isdigit() or len(phone) != 10:
            return {"valid": False, "error": "Phone must be 10 digits"}

        if phone[0] not in "6789":
            return {"valid": False, "error": "Indian mobile numbers start with 6, 7, 8, or 9"}

        return {
            "valid": True,
            "phone": phone,
            "formatted": f"+91 {phone[:5]} {phone[5:]}",
        }

    def validate_aadhaar(self, aadhaar: str) -> Dict[str, Any]:
        """Validate Aadhaar number format (Verhoeff check)."""
        aadhaar = aadhaar.strip().replace(" ", "").replace("-", "")

        if not aadhaar.isdigit() or len(aadhaar) != 12:
            return {"valid": False, "error": "Aadhaar must be 12 digits"}

        # Verhoeff algorithm tables
        d = [
            [0,1,2,3,4,5,6,7,8,9],
            [1,2,3,4,0,6,7,8,9,5],
            [2,3,4,0,1,7,8,9,5,6],
            [3,4,0,1,2,8,9,5,6,7],
            [4,0,1,2,3,9,5,6,7,8],
            [5,9,8,7,6,0,4,3,2,1],
            [6,5,9,8,7,1,0,4,3,2],
            [7,6,5,9,8,2,1,0,4,3],
            [8,7,6,5,9,3,2,1,0,4],
            [9,8,7,6,5,4,3,2,1,0],
        ]
        p = [
            [0,1,2,3,4,5,6,7,8,9],
            [1,5,7,6,2,8,3,0,9,4],
            [5,8,0,3,7,9,6,1,4,2],
            [8,9,1,6,0,4,3,5,2,7],
            [9,4,5,3,1,2,6,8,7,0],
            [4,2,8,6,5,7,3,9,0,1],
            [2,7,9,3,8,0,6,4,1,5],
            [7,0,4,6,9,1,3,2,5,8],
        ]
        inv = [0,4,3,2,1,5,6,7,8,9]

        checksum = 0
        for i, digit in enumerate(reversed(aadhaar)):
            checksum = d[checksum][p[i % 8][int(digit)]]

        if checksum != 0:
            return {"valid": False, "error": "Invalid Aadhaar number (checksum mismatch)"}

        return {
            "valid": True,
            "aadhaar": aadhaar,
            "formatted": "-".join(aadhaar[i:i+4] for i in range(0, 12, 4)),
            "masked": f"XXXX XXXX {aadhaar[-4:]}",
        }

    def validate_pan(self, pan: str) -> Dict[str, Any]:
        """Validate PAN card number format."""
        import re
        pan = pan.strip().upper()

        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
        if not re.match(pattern, pan):
            return {"valid": False, "error": "Invalid PAN format. Must be AAAAA9999A"}

        # Validate issuing authority (4th char)
        issuing = {
            "P": "Individual", "C": "Company", "H": "HUF",
            "F": "Firm", "A": "Association of Persons",
            "T": "Trust", "L": "Local Authority",
            "J": "Artificial Juridical Person", "G": "Government",
        }
        issuer_type = issuing.get(pan[3], "Unknown")

        return {
            "valid": True,
            "pan": pan,
            "type": issuer_type,
            "masked": f"XXXXX{pan[5:9]}{pan[9]}",
        }


# Singleton
pincode_service = PincodeService()
