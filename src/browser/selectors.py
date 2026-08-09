# Centralized WhatsApp Web Selectors

# Selectors for page ready check
PAGE_READY = 'div[id="app"]'
MAIN_CHAT_LIST = 'div[id="pane-side"]'
QR_CODE_CANVAS = 'canvas[aria-label="Scan me!"]'

# Selectors for incoming call detection and action
INCOMING_CALL_MODAL = [
    'div[data-testid="incoming-call-popup"]',
    'div[title*="Incoming call"]',
    'div[title*="Panggilan masuk"]',
    'div:has-text("Incoming voice call")',
    'div:has-text("Panggilan suara masuk")',
    'div:has-text("Incoming call")',
    'div[aria-label*="panggilan"]'
]

ACCEPT_CALL_BUTTON = [
    'button[data-testid="incoming-call-accept"]',
    'button[aria-label="Accept voice call"]',
    'button[aria-label="Terima panggilan suara"]',
    'button[aria-label="Accept"]',
    'button[aria-label="Jawab"]',
    'button:has-text("Accept")',
    'button:has-text("Jawab")',
    'button:has-text("Terima")',
    'span[data-icon="phone-call"]',
    'span[data-icon="phone"]'
]

REJECT_CALL_BUTTON = [
    'button[data-testid="incoming-call-decline"]',
    'button[aria-label="Decline"]',
    'button[aria-label="Tolak"]',
    'button:has-text("Decline")',
    'button:has-text("Tolak")'
]

# Active call state indicators
ACTIVE_CALL_BAR = [
    'div[data-testid="active-call-bar"]',
    'div[title*="Call in progress"]',
    'div:has-text("Call in progress")',
    'div:has-text("Panggilan berlangsung")',
    'span[data-icon="phone-cross"]'
]

END_CALL_BUTTON = [
    'button[data-testid="call-end"]',
    'button[aria-label="End call"]',
    'button[aria-label="Akhiri panggilan"]',
    'span[data-icon="phone-cross"]'
]
