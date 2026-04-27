"""
=============================================================================
roi_labels.py — ROI metadata for dashboard display
=============================================================================

PURPOSE
-------
Single source of truth for how each ROI group is named, described, and
displayed in the dashboard. All framing follows the mentor's guidance:
- "signals correlated with X" not "predicts X"
- "proxy for" not "measures"
- "cognitive control" not "decision-making" or "purchase intent"
"""

ROI_META = {
    "visual": {
        "label":       "Visual Cortex",
        "short":       "Visual",
        "brain_area":  "Occipital lobe",
        "ad_angle":    "Proxy for visual scene registration",
        "explain":     (
            "These regions handle the first stage of visual processing — light, contrast, "
            "colour, edges, and form. Higher activation is correlated with the creative "
            "registering strongly as a visual stimulus. Not a measure of aesthetic quality."
        ),
        "marketing":   "Low visual signal often points to low-contrast or slow-moving "
                       "opening frames. Useful for comparing visual styles, not for "
                       "predicting whether someone will like what they see.",
        "color":       "#4361EE",
        "icon":        "👁",
    },
    "motion": {
        "label":       "Motion Areas",
        "short":       "Motion",
        "brain_area":  "Temporal-occipital junction",
        "ad_angle":    "Proxy for dynamic visual processing",
        "explain":     (
            "Area MT and surrounding regions respond to moving objects, camera cuts, "
            "and optic flow. Activation here is correlated with how much dynamic visual "
            "change the ad contains — not whether that change is effective."
        ),
        "marketing":   "Fast-cut ads will reliably score higher here than slow, static ones. "
                       "This is a style signal, not a quality signal. Useful for understanding "
                       "the visual rhythm of different creative approaches.",
        "color":       "#7209B7",
        "icon":        "⚡",
    },
    "auditory": {
        "label":       "Auditory Cortex",
        "short":       "Audio",
        "brain_area":  "Superior temporal gyrus",
        "ad_angle":    "Proxy for auditory stimulus processing",
        "explain":     (
            "Primary auditory cortex and surrounding belt regions process pitch, rhythm, "
            "speech melody, and complex sounds. Activation is correlated with how "
            "much auditory content the brain is processing — not whether it's enjoyed."
        ),
        "marketing":   "Useful for comparing music tracks, voiced vs. unvoiced ads, "
                       "or different voiceover styles. A strong audio signal means "
                       "the sound is being actively processed.",
        "color":       "#F72585",
        "icon":        "🎵",
    },
    "language": {
        "label":       "Language Network",
        "short":       "Language",
        "brain_area":  "Inferior frontal gyrus (Broca's area)",
        "ad_angle":    "Proxy for verbal content processing",
        "explain":     (
            "Broca's area is associated with speech comprehension, reading text on screen, "
            "and semantic processing. Higher activation is correlated with the brain "
            "actively engaging with verbal content — not with message clarity or persuasion."
        ),
        "marketing":   "Compare taglines, voiceover scripts, or on-screen text. "
                       "A low language signal may mean verbal content is being ignored "
                       "or processed passively. Treat as a hypothesis, not a verdict.",
        "color":       "#3A86FF",
        "icon":        "💬",
    },
    "memory": {
        "label":       "Memory-correlated Regions",
        "short":       "Memory",
        "brain_area":  "Parahippocampal cortex",
        "ad_angle":    "Proxy for scene memory encoding processes",
        "explain":     (
            "Parahippocampal and temporal-fusiform regions are associated with scene and "
            "context memory. Activation here is correlated with memory encoding processes — "
            "not a direct measure of whether someone will recall the brand or message."
        ),
        "marketing":   "Of the 8 groups, this is most commonly cited in neuromarketing "
                       "literature as correlated with later recall. Treat as a useful "
                       "signal, not a recall guarantee. High motion with low memory "
                       "signal may indicate stimulation without retention.",
        "color":       "#06D6A0",
        "icon":        "🧠",
    },
    "attention": {
        "label":       "Attention Network",
        "short":       "Attention",
        "brain_area":  "Intraparietal sulcus",
        "ad_angle":    "Proxy for sustained attentional engagement",
        "explain":     (
            "The intraparietal sulcus is a hub of the dorsal attention network — "
            "associated with directing and sustaining attention over time. "
            "Activation is correlated with attentional engagement, not with interest "
            "or preference."
        ),
        "marketing":   "The time series view is more valuable than the summary score here. "
                       "A declining attention signal over time shows where the ad loses "
                       "people. A rising signal shows a slow-build creative.",
        "color":       "#FFB703",
        "icon":        "🎯",
    },
    "emotion": {
        "label":       "Emotion-correlated Regions",
        "short":       "Emotion",
        "brain_area":  "Temporal pole / superior temporal sulcus",
        "ad_angle":    "Proxy for emotional and social stimulus processing",
        "explain":     (
            "Temporal pole and superior temporal regions are associated with processing "
            "the emotional and social content of stimuli — faces, emotional voices, "
            "and socially meaningful scenes. Activation is correlated with emotional "
            "processing, not with positive sentiment specifically."
        ),
        "marketing":   "Look at the time series to find the peak emotion second — "
                       "that's where the emotional climax of the ad sits. "
                       "If it occurs after second 10, many scroll-feed viewers may "
                       "never reach it.",
        "color":       "#FB5607",
        "icon":        "❤️",
    },
    "decision": {
        "label":       "Cognitive Control Regions",
        "short":       "Cognitive",
        "brain_area":  "Dorsolateral prefrontal cortex",
        "ad_angle":    "Proxy for executive function and task engagement",
        "explain":     (
            "Dorsolateral prefrontal cortex and inferior frontal junction are associated "
            "with cognitive control, working memory, and task switching. "
            "Activation is correlated with active cognitive engagement with the content — "
            "not with decision-making, intent, or purchase likelihood."
        ),
        "marketing":   "Higher signal here suggests the ad is demanding more cognitive "
                       "processing — which may reflect complexity, text-heavy content, "
                       "or unfamiliar concepts. Not inherently good or bad. "
                       "Do not interpret as purchase intent.",
        "color":       "#118AB2",
        "icon":        "⚖️",
    },
}

ROI_ORDER        = ["visual", "motion", "auditory", "language", "memory", "attention", "emotion", "decision"]
ROI_SHORT_LABELS = {k: v["short"] for k, v in ROI_META.items()}
ROI_COLORS       = {k: v["color"] for k, v in ROI_META.items()}
HERO_ROIS        = ["memory", "attention"]

# ── Failure / engagement pattern definitions ──────────────────────────────────
# Used by the Creative Diagnosis section in the dashboard.
# Pattern names map to attention_pattern values from derived_metrics table.

PATTERN_META = {
    "hook_and_drop": {
        "label":      "📉 Hook & Drop",
        "color":      "#DC2626",
        "summary":    "Strong opening, rapid disengagement",
        "detail":     (
            "Predicted attention activates strongly in the first few seconds then "
            "declines consistently. The creative is stopping the scroll — but likely "
            "losing viewers before the message lands. The hook is working. "
            "The mid-section probably isn't."
        ),
        "suggestion": "Tighten the mid-section or improve narrative continuation. "
                      "Test a version where the energy or visual dynamism after second 3 "
                      "matches the opening. Ask: what reason does the viewer have to stay?",
        "test_next":  "Test alternative mid-section pacing — faster cuts, earlier payoff, "
                      "or a second visual hook at second 5–7.",
    },
    "slow_build": {
        "label":      "📈 Slow Build",
        "color":      "#059669",
        "summary":    "Rising engagement — weak opening",
        "detail":     (
            "Predicted attention signal increases over the duration of the ad. "
            "The payoff is real but it arrives late. In short-form scroll feeds "
            "where most viewers decide within 3 seconds, many may not reach it."
        ),
        "suggestion": "Front-load more of the creative's best material. "
                      "Test a version that opens with a face, motion, or text hook "
                      "before transitioning into the build.",
        "test_next":  "Test an alternative opening — lead with your strongest frame "
                      "from the second half of the current cut.",
    },
    "sustained": {
        "label":      "➡️ Sustained",
        "color":      "#4361EE",
        "summary":    "Consistent signal throughout",
        "detail":     (
            "Predicted attention signal is relatively flat — neither building nor "
            "decaying significantly. Check the absolute level: sustained high is "
            "the ideal outcome. Sustained low means no moment is generating strong "
            "predicted attentional signal."
        ),
        "suggestion": "If the absolute level is low, introduce a stronger visual or "
                      "emotional peak. If it is high, this is a stable creative — "
                      "test whether a stronger hook can push it further.",
        "test_next":  "Introduce one deliberate motion or emotional trigger earlier — "
                      "faces, unexpected visuals, or a pace change — and compare.",
    },
}

# Additional diagnostic patterns derived from combinations of metrics
DIAGNOSTIC_RULES = [
    {
        "id":        "high_motion_low_memory",
        "label":     "⚡🧠 Overstimulated — High Motion, Low Memory Signal",
        "condition": lambda d: (
            d.get("motion_score", 0) is not None and
            d.get("memory_score", 0) is not None and
            d.get("motion_score", 0) > 0.04 and
            d.get("memory_score", 0) < 0.03
        ),
        "detail": (
            "High dynamic visual activity with low memory-correlated signal. "
            "The creative is visually busy but may not be generating the slower, "
            "consolidating processes associated with scene memory encoding. "
            "Stimulation without retention."
        ),
        "test_next": "Introduce a moment of visual calm — a held shot, a face, or a "
                     "static brand frame — and test whether memory signal improves.",
    },
    {
        "id":        "peak_emotion_late",
        "label":     "❤️⏱ Emotional Peak Too Late",
        "condition": lambda d: (
            d.get("peak_emotion_second") is not None and
            d.get("peak_emotion_second", 0) > 10
        ),
        "detail": (
            "The predicted emotional peak occurs after second 10. In short-form "
            "feeds most viewers decide within 3–5 seconds — many will not reach "
            "this moment. The emotional payoff exists; it just arrives too late."
        ),
        "test_next": "Test a version that introduces an earlier emotional beat — "
                     "a face with expression, an emotionally charged audio moment, "
                     "or a reordered sequence that front-loads the climax.",
    },
    {
        "id":        "weak_hook",
        "label":     "🎣 Weak Hook Signal",
        "condition": lambda d: (
            d.get("hook_strength") is not None and
            d.get("hook_strength", 0) < 0.02
        ),
        "detail": (
            "Hook strength — proxy for early scroll-stopping potential — is low. "
            "The opening frames may lack sufficient visual contrast, motion, or "
            "emotional content to generate strong predicted engagement signals "
            "in the first 3 seconds."
        ),
        "test_next": "Test alternative opening frames: a face in motion, unexpected "
                     "visual contrast, bold on-screen text, or a sound that demands "
                     "attention before the main content begins.",
    },
]
