import re

# Centralized configuration dictionaries/sets
DONATABLE_LABELS = {
    "book", "backpack", "handbag", "suitcase", "bottle", "cup", "bowl", 
    "spoon", "fork", "knife", "chair", "couch", "bed", "dining table", 
    "laptop", "keyboard", "mouse", "cell phone", "tv", "clock", "teddy bear", 
    "tie", "umbrella", "scissors", "toothbrush", "hair drier", "vase",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake"
}

NON_DONATABLE_LABELS = {
    # Scenes/Environment
    "person", "tree", "cloud", "sky", "road", "building", "grass", "animal", "plant",
    # Vehicles & Infrastructure
    "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    # Animals
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"
}

DONATION_CATEGORY_MAP = {
    "book": "Books",
    "banana": "Food",
    "apple": "Food",
    "sandwich": "Food",
    "orange": "Food",
    "broccoli": "Food",
    "carrot": "Food",
    "hot dog": "Food",
    "pizza": "Food",
    "donut": "Food",
    "cake": "Food",
    "backpack": "Education",
    "handbag": "Clothing",
    "suitcase": "Household",
    "bottle": "Household",
    "cup": "Household",
    "bowl": "Household",
    "spoon": "Household",
    "fork": "Household",
    "knife": "Household",
    "chair": "Furniture",
    "couch": "Furniture",
    "bed": "Furniture",
    "dining table": "Furniture",
    "laptop": "Electronics",
    "keyboard": "Electronics",
    "mouse": "Electronics",
    "cell phone": "Electronics",
    "tv": "Electronics",
    "clock": "Household",
    "teddy bear": "Toys",
    "tie": "Clothing",
    "umbrella": "Household",
    "scissors": "Education",
    "toothbrush": "Other",
    "hair drier": "Electronics",
    "vase": "Household",
    # Review required items
    "remote": "Electronics",
    "microwave": "Electronics",
    "oven": "Furniture",
    "toaster": "Electronics",
    "sink": "Furniture",
    "refrigerator": "Electronics",
    "frisbee": "Toys",
    "skis": "Toys",
    "snowboard": "Toys",
    "sports ball": "Toys",
    "kite": "Toys",
    "baseball bat": "Toys",
    "baseball glove": "Toys",
    "skateboard": "Toys",
    "surfboard": "Toys",
    "tennis racket": "Toys",
    "potted plant": "Household",
    "toilet": "Household"
}

POLISHED_LABELS = {
    "tv": "Television",
    "cell phone": "Mobile Phone",
    "mouse": "Computer Mouse",
    "remote": "Remote Control",
    "hair drier": "Hair Drier",
    "sports ball": "Sports Ball",
    "baseball bat": "Baseball Bat",
    "baseball glove": "Baseball Glove",
    "wine glass": "Wine Glass",
    "dining table": "Dining Table",
    "potted plant": "Potted Plant"
}

class DonationEligibilityService:
    @classmethod
    def get_display_label(cls, label: str) -> str:
        """
        Formats label nicely for display.
        """
        norm = cls.normalize_label(label)
        if norm in POLISHED_LABELS:
            return POLISHED_LABELS[norm]
        return label.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def normalize_label(label: str) -> str:
        """
        Normalize label by converting to lowercase, stripping,
        and replacing hyphens/underscores/etc. with space.
        """
        if not label:
            return ""
        val = label.lower().strip()
        val = re.sub(r'[-_]+', ' ', val)
        return val

    @classmethod
    def classify_detection(cls, label: str, category: str | None = None) -> str:
        """
        Classifies detection as DONATABLE, NON_DONATABLE, or REVIEW_REQUIRED.
        """
        norm = cls.normalize_label(label)
        
        # Check explicit lists first
        if norm in DONATABLE_LABELS:
            return "DONATABLE"
        if norm in NON_DONATABLE_LABELS:
            return "NON_DONATABLE"
        
        # Partial match checks to catch similar categories (e.g. "wild animal" containing "animal")
        for bad in NON_DONATABLE_LABELS:
            if bad in norm:
                return "NON_DONATABLE"
                
        for good in DONATABLE_LABELS:
            if good in norm:
                return "DONATABLE"

        return "REVIEW_REQUIRED"

    @classmethod
    def is_donatable(cls, label: str) -> bool:
        """
        Returns True if the label is classified as DONATABLE.
        """
        return cls.classify_detection(label) == "DONATABLE"

    @classmethod
    def get_donation_category(cls, label: str) -> str:
        """
        Resolves the Donate category for a label, fallback to 'Other'.
        """
        norm = cls.normalize_label(label)
        return DONATION_CATEGORY_MAP.get(norm, "Other")

    @classmethod
    def get_rejection_reason(cls, label: str) -> str | None:
        """
        Returns a human-readable rejection reason if classified as NON_DONATABLE.
        """
        status = cls.classify_detection(label)
        if status != "NON_DONATABLE":
            return None
            
        norm = cls.normalize_label(label)
        if norm == "person":
            return "ignored because it is a person"
        if norm in {"tree", "cloud", "sky", "road", "building", "grass", "plant"}:
            return "ignored because it is an environmental/background object"
        if norm in {"car", "bus", "truck", "motorcycle", "bicycle", "airplane", "boat"}:
            return "ignored because it is a vehicle"
        if norm in {"traffic light", "fire hydrant", "stop sign", "parking meter", "bench"}:
            return "ignored because it is public infrastructure"
        return f"ignored because '{label}' is not an eligible donation item"
