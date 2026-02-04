import pygame
import numpy as np
from enum import IntEnum
import math

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
CELL_STATES = IntEnum('CellState', {'EMPTY': 0, 'TREE': 1, 'BURNING': 2, 'BURNT': 3})
GRID_WIDTH, GRID_HEIGHT = 120, 80
PANEL_WIDTH = 320
FPS, SIMULATION_SPEED = 60, 3

# Premium light theme - clean and breathable
COLORS = {
    'EMPTY': (255, 255, 255), 'TREE': (34, 139, 34), 'BURNING': (230, 50, 0), 'BURNT': (65, 65, 70),
    'BG': (240, 242, 245), 'PANEL_BG': (255, 255, 255), 'PANEL_BORDER': (220, 222, 228),
    'TEXT': (30, 35, 45), 'TEXT_DIM': (110, 120, 135), 'ACCENT': (0, 122, 255),
    'ACCENT_GLOW': (150, 200, 255), 'SUCCESS': (40, 167, 69), 'DANGER': (220, 53, 69),
    'SLIDER_BG': (235, 238, 245), 'SLIDER_FILL': (0, 122, 255), 'BUTTON_BG': (248, 249, 252),
    'BUTTON_HOVER': (235, 245, 255), 'CARD_BG': (250, 251, 253)
}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def clamp(val, lo, hi): return max(lo, min(hi, val))
def lerp(a, b, t): return a + (b - a) * t
def ease_out_cubic(t): return 1 - pow(1 - t, 3)

def draw_rounded_rect(surface, color, rect, radius=8, alpha=255):
    """Efficient rounded rectangle with optional alpha"""
    if alpha < 255:
        temp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(temp, (*color, alpha), temp.get_rect(), border_radius=radius)
        surface.blit(temp, rect.topleft)
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_glow_circle(surface, color, center, radius, glow_radius=4):
    """Draw circle with subtle glow effect"""
    for i in range(glow_radius, 0, -1):
        alpha = int(40 * (1 - i / glow_radius))
        temp = pygame.Surface((radius * 2 + i * 4, radius * 2 + i * 4), pygame.SRCALPHA)
        pygame.draw.circle(temp, (*color, alpha), (radius + i * 2, radius + i * 2), radius + i)
        surface.blit(temp, (center[0] - radius - i * 2, center[1] - radius - i * 2))
    pygame.draw.circle(surface, color, center, radius)

# ═══════════════════════════════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════
class Slider:
    """Premium slider with smooth interactions"""
    def __init__(self, x, y, w, h, min_v, max_v, val, label, key):
        self.rect, self.min_v, self.max_v, self.val = pygame.Rect(x, y, w, h), min_v, max_v, val
        self.label, self.key, self.dragging = label, key, False
    
    def handle_x(self): return int(self.rect.x + (self.val - self.min_v) / (self.max_v - self.min_v) * self.rect.width)
    
    def update_val(self, mx): self.val = clamp(self.min_v + (mx - self.rect.x) / self.rect.width * (self.max_v - self.min_v), self.min_v, self.max_v)
    
    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and self.rect.inflate(20, 20).collidepoint(e.pos):
            self.dragging = True; self.update_val(e.pos[0]); return True
        if e.type == pygame.MOUSEBUTTONUP: self.dragging = False
        if e.type == pygame.MOUSEMOTION and self.dragging: self.update_val(e.pos[0]); return True
        return False
    
    def draw(self, surf, font, small_font):
        # Track background with rounded ends
        pygame.draw.rect(surf, COLORS['SLIDER_BG'], self.rect, border_radius=4)
        # Filled portion with gradient feel
        fill_w = int((self.val - self.min_v) / (self.max_v - self.min_v) * self.rect.width)
        if fill_w > 0: pygame.draw.rect(surf, COLORS['SLIDER_FILL'], pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height), border_radius=4)
        # Handle
        hx = self.handle_x()
        pygame.draw.circle(surf, COLORS['TEXT'], (hx, self.rect.centery), 7)
        pygame.draw.circle(surf, COLORS['ACCENT'], (hx, self.rect.centery), 5)
        # Label
        surf.blit(font.render(self.label, True, COLORS['TEXT_DIM']), (self.rect.x, self.rect.y - 26))
        # Value display
        val_surf = small_font.render(f"{self.val:.2f}", True, COLORS['TEXT_DIM'])
        surf.blit(val_surf, (self.rect.right - val_surf.get_width(), self.rect.y - 26))


class Button:
    """Premium button with hover effects and smooth animations"""
    def __init__(self, x, y, w, h, text, action):
        self.rect, self.text, self.action, self.hover = pygame.Rect(x, y, w, h), text, action, False
    
    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION: self.hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(e.pos): self.action(); return True
        return False
    
    def draw(self, surf, font):
        color = COLORS['BUTTON_HOVER'] if self.hover else COLORS['BUTTON_BG']
        draw_rounded_rect(surf, color, self.rect, radius=10)
        if self.hover: pygame.draw.rect(surf, COLORS['ACCENT'], self.rect, width=2, border_radius=10)
        text_surf = font.render(self.text, True, COLORS['ACCENT'] if self.hover else COLORS['TEXT'])
        surf.blit(text_surf, text_surf.get_rect(center=self.rect.center))


class WindCompass:
    """Beautiful wind direction indicator with animated arrow"""
    def __init__(self, x, y, size):
        self.cx, self.cy, self.size = x + size // 2, y + size // 2, size
        self.radius = size // 2 - 20
    
    def draw(self, surf, font, small_font, direction, strength):
        # Outer glow ring
        pygame.draw.circle(surf, COLORS['PANEL_BORDER'], (self.cx, self.cy), self.radius + 3, 2)
        pygame.draw.circle(surf, COLORS['SLIDER_BG'], (self.cx, self.cy), self.radius, 1)
        
        # Cardinal directions with styled labels
        for angle, lbl in [(0, 'N'), (90, 'E'), (180, 'S'), (270, 'W')]:
            rad = math.radians(angle)
            tx = self.cx + (self.radius + 14) * math.sin(rad)
            ty = self.cy - (self.radius + 14) * math.cos(rad)
            color = COLORS['ACCENT'] if lbl == 'N' else COLORS['TEXT_DIM']
            lbl_surf = small_font.render(lbl, True, color)
            surf.blit(lbl_surf, (tx - lbl_surf.get_width() // 2, ty - lbl_surf.get_height() // 2))
            # Tick marks
            t1x, t1y = self.cx + (self.radius - 6) * math.sin(rad), self.cy - (self.radius - 6) * math.cos(rad)
            t2x, t2y = self.cx + self.radius * math.sin(rad), self.cy - self.radius * math.cos(rad)
            pygame.draw.line(surf, COLORS['PANEL_BORDER'], (t1x, t1y), (t2x, t2y), 2)
        
        # Wind direction arrow with dynamic length
        wind_rad = math.radians(direction)
        arrow_len = self.radius * (0.4 + strength * 0.5)
        end_x, end_y = self.cx + arrow_len * math.sin(wind_rad), self.cy - arrow_len * math.cos(wind_rad)
        
        # Arrow shaft with glow
        for i, alpha in enumerate([60, 100, 180]):
            width = 5 - i
            temp = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            pygame.draw.line(temp, (*COLORS['ACCENT'], alpha), (self.cx - (self.cx - self.size // 2), self.cy - (self.cy - self.size // 2)), (end_x - (self.cx - self.size // 2), end_y - (self.cy - self.size // 2)), width)
        pygame.draw.line(surf, COLORS['ACCENT'], (self.cx, self.cy), (end_x, end_y), 3)
        
        # Arrowhead
        head_size = 12
        for offset in [-25, 25]:
            hx = end_x - head_size * math.sin(wind_rad + math.radians(offset))
            hy = end_y + head_size * math.cos(wind_rad + math.radians(offset))
            pygame.draw.line(surf, COLORS['ACCENT'], (end_x, end_y), (hx, hy), 3)
        
        # Center dot
        pygame.draw.circle(surf, COLORS['ACCENT'], (self.cx, self.cy), 4)
        
        # Direction degrees and strength below compass
        dir_text = f"{int(direction)}°"
        dir_surf = font.render(dir_text, True, COLORS['TEXT'])
        surf.blit(dir_surf, (self.cx - dir_surf.get_width() // 2, self.cy + self.radius + 22))
        
        strength_text = f"Strength: {strength:.0%}"
        str_surf = small_font.render(strength_text, True, COLORS['TEXT_DIM'])
        surf.blit(str_surf, (self.cx - str_surf.get_width() // 2, self.cy + self.radius + 44))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SIMULATION CLASS
# ═══════════════════════════════════════════════════════════════════════════════
class ForestFireSimulation:
    """Forest fire cellular automata with premium UI"""
    
    def __init__(self):
        pygame.init()
        self._setup_display()
        pygame.display.set_caption("🌲 Forest Fire Simulation")
        self.clock = pygame.time.Clock()
        
        # Fonts - clean modern typeface
        self.font = pygame.font.SysFont('Segoe UI', 16)
        self.small_font = pygame.font.SysFont('Segoe UI', 13)
        self.title_font = pygame.font.SysFont('Segoe UI', 22, bold=True)
        self.stat_font = pygame.font.SysFont('Segoe UI', 14)
        
        # Simulation state
        self.grid = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)
        self.running, self.paused, self.last_step = False, False, 0
        
        # Parameters
        self.tree_density, self.wind_dir, self.wind_str, self.moisture, self.temperature = 0.6, 0.0, 0.5, 0.2, 25.0
        self.fire_prob = 0.3  # Computed from other params
        
        # Initialize UI
        self._create_ui()
        self._init_forest()
    
    def _setup_display(self):
        """Setup fullscreen display with dynamic grid sizing"""
        info = pygame.display.Info()
        self.win_w, self.win_h = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.FULLSCREEN)
        
        # Calculate cell size to fill available space
        grid_area_w = self.win_w - PANEL_WIDTH
        self.cell_size = max(min(grid_area_w // GRID_WIDTH, self.win_h // GRID_HEIGHT), 6)
        self.grid_px_w = GRID_WIDTH * self.cell_size
        self.grid_px_h = GRID_HEIGHT * self.cell_size
        
        # Center grid vertically
        self.grid_offset_y = (self.win_h - self.grid_px_h) // 2
    
    def _create_ui(self):
        """Create all UI components with proper spacing"""
        px = self.win_w - PANEL_WIDTH + 28  # Panel x with padding
        pw = PANEL_WIDTH - 56  # Usable width
        
        # Sliders with generous vertical spacing
        sy = 90
        sp = 58
        self.sliders = [
            Slider(px, sy, pw, 8, 0.1, 0.9, 0.6, "Tree Density", "1"),
            Slider(px, sy + sp, pw, 8, 0, 360, 0, "Wind Direction", "2"),
            Slider(px, sy + sp * 2, pw, 8, 0, 1, 0.5, "Wind Strength", "3"),
            Slider(px, sy + sp * 3, pw, 8, 0, 0.5, 0.2, "Moisture", "4"),
            Slider(px, sy + sp * 4, pw, 8, 0, 50, 25, "Temperature (°C)", "5"),
        ]
        
        # Wind compass centered
        compass_size = 130
        self.compass = WindCompass(px + (pw - compass_size) // 2, sy + sp * 5 + 10, compass_size)
        
        # Buttons below compass
        by = sy + sp * 5 + compass_size + 70
        bh, bs = 42, 52
        self.buttons = [
            Button(px, by, pw, bh, "🔥  Start Fire", self._start_fire),
            Button(px, by + bs, pw, bh, "🌲  Reset Forest", self._reset_forest),
            Button(px, by + bs * 2, pw, bh, "⏯  Play / Pause", self._toggle_pause),
            Button(px, by + bs * 3, pw, bh, "⏭  Step Forward", self._step_forward),
            Button(px, by + bs * 4, pw, bh, "🎲  Randomize", self._randomize),
        ]
        
        self.stats_y = by + bs * 5 + 20
    
    def _init_forest(self):
        """Initialize forest with current tree density"""
        self.grid = np.random.choice([CELL_STATES.EMPTY, CELL_STATES.TREE], (GRID_HEIGHT, GRID_WIDTH), p=[1 - self.tree_density, self.tree_density]).astype(np.uint8)
    
    # ─── Actions ───
    def _start_fire(self):
        trees = np.argwhere(self.grid == CELL_STATES.TREE)
        if len(trees) > 0:
            for y, x in trees[np.random.choice(len(trees), min(3, len(trees)), replace=False)]:
                self.grid[y, x] = CELL_STATES.BURNING
            self.running = True
    
    def _reset_forest(self):
        self.tree_density = self.sliders[0].val
        self._init_forest()
        self.running, self.paused = False, False
    
    def _toggle_pause(self): self.paused = not self.paused
    def _step_forward(self): self._simulate_step()
    
    def _randomize(self):
        self.sliders[0].val = np.random.uniform(0.3, 0.8)
        self.sliders[1].val = np.random.uniform(0, 360)
        self.sliders[2].val = np.random.uniform(0.2, 0.9)
        self.sliders[3].val = np.random.uniform(0, 0.4)
        self.sliders[4].val = np.random.uniform(10, 45)
        self._sync_params()
        self._reset_forest()
    
    # ─── Simulation Logic ───
    def _get_wind_bias(self, dy, dx):
        if self.wind_str == 0: return 1.0
        angle = math.atan2(dx, -dy) * 180 / math.pi  # Convert to compass bearing (0=N, 90=E)
        diff = abs(angle - self.wind_dir)
        if diff > 180: diff = 360 - diff
        return max(0.1, 1.0 + self.wind_str * math.cos(math.radians(diff)))
    
    def _simulate_step(self):
        new = self.grid.copy()
        burning = np.argwhere(self.grid == CELL_STATES.BURNING)
        new[burning[:, 0], burning[:, 1]] = CELL_STATES.BURNT
        
        for by, bx in burning:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                ny, nx = by + dy, bx + dx
                if 0 <= ny < GRID_HEIGHT and 0 <= nx < GRID_WIDTH and self.grid[ny, nx] == CELL_STATES.TREE:
                    prob = self.fire_prob * self._get_wind_bias(dy, dx) * (1 - self.moisture)
                    if np.random.random() < prob: new[ny, nx] = CELL_STATES.BURNING
        
        self.grid = new
        if not np.any(self.grid == CELL_STATES.BURNING): self.running = False
    
    def _sync_params(self):
        """Sync slider values and compute fire spread probability"""
        self.tree_density, self.wind_dir, self.wind_str = self.sliders[0].val, self.sliders[1].val, self.sliders[2].val
        self.moisture, self.temperature = self.sliders[3].val, self.sliders[4].val
        # Fire probability: increases with temp & wind, decreases with moisture
        temp_factor = clamp((self.temperature - 10) / 40, 0, 1)  # 0 at 10°C, 1 at 50°C
        self.fire_prob = clamp(0.15 + 0.5 * temp_factor + 0.2 * self.wind_str - 0.4 * self.moisture, 0.05, 0.95)
    
    # ─── Rendering ───
    def _draw_grid(self):
        """Render forest grid with cell coloring"""
        cell_colors = [COLORS['EMPTY'], COLORS['TREE'], COLORS['BURNING'], COLORS['BURNT']]
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                color = cell_colors[self.grid[y, x]]
                rect = pygame.Rect(x * self.cell_size, self.grid_offset_y + y * self.cell_size, self.cell_size, self.cell_size)
                pygame.draw.rect(self.screen, color, rect)
    
    def _draw_panel(self):
        """Render control panel with modern card layout"""
        px = self.win_w - PANEL_WIDTH
        
        # Panel background with subtle gradient effect
        draw_rounded_rect(self.screen, COLORS['PANEL_BG'], pygame.Rect(px, 0, PANEL_WIDTH, self.win_h), radius=0)
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (px, 0), (px, self.win_h), 1)
        
        # Title section
        title = self.title_font.render("Controls", True, COLORS['TEXT'])
        self.screen.blit(title, (px + 28, 28))
        
        # Sliders
        for s in self.sliders:
            s.draw(self.screen, self.font, self.small_font)
        
        # Wind compass
        self.compass.draw(self.screen, self.font, self.small_font, self.wind_dir, self.wind_str)
        
        # Buttons
        for b in self.buttons: b.draw(self.screen, self.font)
        
        # Stats card
        card_rect = pygame.Rect(px + 20, self.stats_y, PANEL_WIDTH - 40, 130)
        draw_rounded_rect(self.screen, COLORS['CARD_BG'], card_rect, radius=12)
        
        # Fire probability (computed, read-only) - prominent display
        prob_label = self.font.render("Fire Spread Probability", True, COLORS['TEXT'])
        self.screen.blit(prob_label, (px + 32, self.stats_y + 12))
        prob_val = self.stat_font.render(f"{self.fire_prob:.0%}", True, COLORS['DANGER'])
        self.screen.blit(prob_val, (px + PANEL_WIDTH - 72, self.stats_y + 12))
        
        trees = np.sum(self.grid == CELL_STATES.TREE)
        burning = np.sum(self.grid == CELL_STATES.BURNING)
        burnt = np.sum(self.grid == CELL_STATES.BURNT)
        total = GRID_WIDTH * GRID_HEIGHT
        
        stats = [
            (f"🌲 Trees: {trees}", COLORS['SUCCESS'], trees / total),
            (f"🔥 Burning: {burning}", COLORS['DANGER'], burning / total),
            (f"⬛ Burnt: {burnt}", COLORS['TEXT_DIM'], burnt / total),
        ]
        
        sy = self.stats_y + 44
        for i, (txt, clr, pct) in enumerate(stats):
            self.screen.blit(self.stat_font.render(txt, True, clr), (px + 32, sy + i * 28))
            bar_rect = pygame.Rect(px + 160, sy + i * 28 + 4, 100, 8)
            pygame.draw.rect(self.screen, COLORS['SLIDER_BG'], bar_rect, border_radius=4)
            if pct > 0:
                fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.width * pct), bar_rect.height)
                pygame.draw.rect(self.screen, clr, fill_rect, border_radius=4)

    
    # ─── Event Handling ───
    def _handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return False
            
            for s in self.sliders: s.handle_event(e)
            for b in self.buttons: b.handle_event(e)
            
            # Click grid to ignite
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                if mx < self.grid_px_w:
                    gx, gy = mx // self.cell_size, (my - self.grid_offset_y) // self.cell_size
                    if 0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT and self.grid[gy, gx] == CELL_STATES.TREE:
                        self.grid[gy, gx] = CELL_STATES.BURNING
                        self.running = True
        return True
    
    # ─── Main Loop ───
    def run(self):
        while True:
            if not self._handle_events(): break
            self._sync_params()
            
            # Simulation timestep
            now = pygame.time.get_ticks()
            if self.running and not self.paused and now - self.last_step > 1000 / SIMULATION_SPEED:
                self._simulate_step()
                self.last_step = now
            
            # Render
            self.screen.fill(COLORS['BG'])
            self._draw_grid()
            self._draw_panel()
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()


if __name__ == "__main__":
    ForestFireSimulation().run()
