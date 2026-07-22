from typing import List

class PackagingService:
    CHECKLISTS = {
        "Books": [
            "Stack books neatly by size to maximize space",
            "Wrap items/boxes in plastic or wrap to protect from moisture",
            "Pack in a strong, double-walled cardboard box",
            "Avoid overloading boxes to prevent bottom tearing (max 15kg)"
        ],
        "Clothing": [
            "Wash and thoroughly dry all items before packing",
            "Fold clothing neatly to minimize wrinkling and maximize space",
            "Separate items by type (e.g., shirts, pants, jackets) if possible",
            "Pack in clean, heavy-duty plastic bags or sturdy boxes"
        ],
        "Electronics": [
            "Switch off all devices completely",
            "Remove any batteries or SIM cards; wipe personal data from memory",
            "Include chargers, power bricks, and accessories if available",
            "Use bubble wrap or protective padding to prevent impact damage"
        ],
        "Food": [
            "Verify all items are well within their expiry/best-by dates",
            "Ensure original manufacturer seals are intact and unopened",
            "Do not donate expired, dented, or opened packaging",
            "Separate glass or fragile containers to avoid breakage"
        ],
        "Furniture": [
            "Clean and dust the surfaces thoroughly",
            "Secure or remove loose parts (drawers, shelves, cushions)",
            "Measure and record exact dimensions for vehicle clearance",
            "Ensure clear, unobstructed pathway from items to pickup location"
        ],
        "Utensils": [
            "Clean, dry, and wipe all items thoroughly",
            "Wrap sharp knives or fragile ceramic/glass pieces separately",
            "Stack pots, pans, and plates nested securely with paper separators",
            "Pack in heavy-duty boxes with crumpled paper/bubble wrap padding"
        ]
    }

    DEFAULT_CHECKLIST = [
        "Clean all items thoroughly before packaging",
        "Pack items securely in boxes or clean bags to prevent movement",
        "Clearly label the box with the donation contents and reference number",
        "Store the packed boxes in a dry place until collection"
    ]

    @classmethod
    def get_tips_for_categories(cls, categories: List[str]) -> dict:
        """
        Returns a dictionary of category-specific checklist instructions based on list of categories.
        """
        res = {}
        for cat in categories:
            # Match case insensitively but return nice keys
            matched_key = None
            for key in cls.CHECKLISTS:
                if key.lower() == cat.lower():
                    matched_key = key
                    break
            
            if matched_key:
                res[matched_key] = cls.CHECKLISTS[matched_key]
            else:
                # Map alternate category names to standard lists
                if "education" in cat.lower() or "study" in cat.lower():
                    res["Education/Books"] = cls.CHECKLISTS["Books"]
                elif "household" in cat.lower() or "kitchen" in cat.lower():
                    res["Household/Utensils"] = cls.CHECKLISTS["Utensils"]
                elif "toy" in cat.lower() or "game" in cat.lower():
                    res["Toys/Electronics"] = cls.CHECKLISTS["Electronics"]
                else:
                    res[cat] = cls.DEFAULT_CHECKLIST
        
        # Ensure there is at least a default checklist if empty
        if not res:
            res["General Items"] = cls.DEFAULT_CHECKLIST
        return res
