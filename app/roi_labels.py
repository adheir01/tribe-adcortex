"""
=============================================================================
roi_labels.py — ROI metadata for dashboard display
=============================================================================

PURPOSE
-------
Single source of truth for how each ROI group is named, described, and
displayed in the dashboard. Separating this from charts.py means you can
update labels and colours in one place without touching visualisation code.

This is the "data dictionary" layer that translates neuroscience terminology
into marketing language your audience actually understands.
"""

# ── ROI display metadata ──────────────────────────────────────────────────────
# Keys match the roi_group values stored in PostgreSQL

ROI_META = {
    "visual": {
        "label":       "Visual Cortex",
        "short":       "Visual",
        "hcp_regions": ["V1", "V2", "V4"],
        "brain_area":  "Occipital lobe",
        "ad_angle":    "Raw visual attention",
        "explain":     (
            "V1 and V2 are the brain's first visual processing stages — they respond "
            "to light, contrast, colour, and edges. High activation here means the "
            "creative is visually registering strongly. V4 adds colour and form processing."
        ),
        "marketing":   "A strong visual score means the creative immediately catches "
                       "the eye. Low visual activation often means the opening frames "
                       "are too slow or low-contrast.",
        "color":       "#4361EE",
        "icon":        "👁",
    },
    "motion": {
        "label":       "Motion Areas",
        "short":       "Motion",
        "hcp_regions": ["MT", "MST", "V3CD"],
        "brain_area":  "Temporal-occipital junction",
        "ad_angle":    "Dynamic scene processing",
        "explain":     (
            "Area MT (middle temporal) is the brain's dedicated motion detector. "
            "It fires strongly for moving objects, camera cuts, and dynamic visual changes. "
            "MST extends to optic flow — the feeling of moving through space."
        ),
        "marketing":   "High motion scores favour fast-cut creatives with strong camera "
                       "movement. Slow, static ads score lower here — which isn't "
                       "always bad if the goal is calm brand building.",
        "color":       "#7209B7",
        "icon":        "⚡",
    },
    "auditory": {
        "label":       "Auditory Cortex",
        "short":       "Audio",
        "hcp_regions": ["A1", "LBelt", "MBelt"],
        "brain_area":  "Superior temporal gyrus",
        "ad_angle":    "Music and voiceover engagement",
        "explain":     (
            "A1 (primary auditory cortex) processes sound at the most basic level — "
            "pitch, volume, rhythm. The lateral and medial belt regions handle more "
            "complex sounds including speech melody and musical patterns."
        ),
        "marketing":   "A strong audio score means the soundtrack or voiceover is "
                       "creating neural engagement. Consider this when A/B testing "
                       "music tracks or comparing voiced vs. silent ads.",
        "color":       "#F72585",
        "icon":        "🎵",
    },
    "language": {
        "label":       "Language Network",
        "short":       "Language",
        "hcp_regions": ["44", "45", "IFSp"],
        "brain_area":  "Inferior frontal gyrus (Broca's area)",
        "ad_angle":    "Verbal messaging comprehension",
        "explain":     (
            "Broca's area (areas 44 and 45) is central to language processing — "
            "understanding speech, reading text on screen, and semantic meaning. "
            "High activation here means the verbal content of the ad is being "
            "actively processed and understood."
        ),
        "marketing":   "Test different taglines, voiceover scripts, or on-screen text. "
                       "A low language score might mean the copy is being ignored or "
                       "is too complex to process quickly.",
        "color":       "#3A86FF",
        "icon":        "💬",
    },
    "memory": {
        "label":       "Memory Encoding",
        "short":       "Memory",
        "hcp_regions": ["PHA1", "PHA2", "TF"],
        "brain_area":  "Parahippocampal cortex",
        "ad_angle":    "Brand recall likelihood",
        "explain":     (
            "The parahippocampal areas (PHA1, PHA2) and temporal-fusiform cortex "
            "are directly involved in encoding new memories — particularly for scenes "
            "and visual contexts. This is the region most predictive of whether someone "
            "will remember the brand or message the next day."
        ),
        "marketing":   "This is arguably the most important metric for brand advertisers. "
                       "High memory scores predict recall in post-campaign surveys. "
                       "If memory is low but attention is high, you have engagement "
                       "without retention — common with visually impressive but brand-light ads.",
        "color":       "#06D6A0",
        "icon":        "🧠",
    },
    "attention": {
        "label":       "Attention Network",
        "short":       "Attention",
        "hcp_regions": ["AIP", "LIPv", "VIP"],
        "brain_area":  "Intraparietal sulcus",
        "ad_angle":    "Sustained attentional engagement",
        "explain":     (
            "The intraparietal sulcus (IPS) is the hub of the dorsal attention network. "
            "It controls where attention is directed and sustains it over time. "
            "AIP (anterior), LIPv (lateral), and VIP (ventral) cover spatial attention, "
            "visual salience tracking, and multisensory attention respectively."
        ),
        "marketing":   "Attention score answers: 'Is the brain staying with this ad?' "
                       "A high early spike that drops off signals the creative loses "
                       "people mid-way. Sustained high attention throughout is rare and "
                       "very valuable.",
        "color":       "#FFB703",
        "icon":        "🎯",
    },
    "emotion": {
        "label":       "Emotion Processing",
        "short":       "Emotion",
        "hcp_regions": ["TGd", "TE1a", "TE1p"],
        "brain_area":  "Temporal pole / superior temporal sulcus",
        "ad_angle":    "Emotional resonance",
        "explain":     (
            "The temporal pole (TGd) and superior temporal regions process the emotional "
            "and social meaning of stimuli — faces, voices with emotional tone, and "
            "socially meaningful scenes. This network is central to empathy and "
            "emotional response to storytelling."
        ),
        "marketing":   "Emotion is a strong predictor of purchase intent and brand affinity. "
                       "Ads that tell human stories, show faces expressing emotion, or use "
                       "emotionally resonant music score highly here. Great for evaluating "
                       "lifestyle vs. product-feature ad concepts.",
        "color":       "#FB5607",
        "icon":        "❤️",
    },
    "decision": {
        "label":       "Prefrontal Cortex",
        "short":       "Decision",
        "hcp_regions": ["p9-46v", "IFJa", "IFJp"],
        "brain_area":  "Dorsolateral prefrontal cortex",
        "ad_angle":    "Cognitive engagement and intent signals",
        "explain":     (
            "The DLPFC (area 9-46) is involved in working memory, reasoning, and "
            "decision-making. The inferior frontal junction (IFJa/p) handles cognitive "
            "control and task switching. High activation here means the creative is "
            "triggering active cognitive processing — the brain is working with the content."
        ),
        "marketing":   "High decision scores are important for direct-response ads "
                       "where you want the viewer thinking about a purchase. Lower scores "
                       "are expected for pure brand awareness plays — which is fine. "
                       "Use this to validate whether your CTA is cognitively landing.",
        "color":       "#118AB2",
        "icon":        "⚖️",
    },
}

# Ordered list for consistent chart display
ROI_ORDER = ["visual", "motion", "auditory", "language", "memory", "attention", "emotion", "decision"]

# Short labels for chart axes
ROI_SHORT_LABELS = {k: v["short"] for k, v in ROI_META.items()}

# Hex colours for chart series
ROI_COLORS = {k: v["color"] for k, v in ROI_META.items()}

# The two "hero" metrics — what matters most for ad recall
HERO_ROIS = ["memory", "attention"]
