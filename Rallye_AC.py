import pygame
import ctypes
from ctypes import c_int32, c_float, c_wchar, Structure
import mmap
import os

# ------SETTINGS---------------------------------------------------------------
freedom_units = True

# Set screen dimensions below
SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 600 

# Set refresh rate below in hz
refresh_rate = 60

# Use fullscreen borderless?
fullscreen = False

# Change to the position of your dash
# Ex: if your main monitor is 1920x1080 and Dash is set up to the right -> '1920, 0'
dash_position = '100, 100'

# -----------------------------------------------------------------------------


# Extract Shared Memory Structures
class SPageFilePhysics(Structure):
    _pack_ = 4
    _fields_ = [
        ('packetId', c_int32),
        ('gas', c_float),
        ('brake', c_float),
        ('fuel', c_float),
        ('gear', c_int32),
        ('rpms', c_int32),
        ('steerAngle', c_float),
        ('speedKmh', c_float),
        ('velocity', c_float * 3),
        ('accG', c_float * 3),
        ('wheelSlip', c_float * 4),
        ('wheelLoad', c_float * 4),
        ('wheelsPressure', c_float * 4),
        ('wheelAngularSpeed', c_float * 4),
        ('tyreWear', c_float * 4),
        ('tyreDirtyLevel', c_float * 4),
        ('tyreCoreTemperature', c_float * 4),
        ('camberRAD', c_float * 4),
        ('suspensionTravel', c_float * 4),
        ('drs', c_float),
        ('tc', c_float),
        ('heading', c_float),
        ('pitch', c_float),
        ('roll', c_float),
        ('cgHeight', c_float),
        ('carDamage', c_float * 5),
        ('numberOfTyresOut', c_int32),
        ('pitLimiterOn', c_int32),
        ('abs', c_float),
        ('kersCharge', c_float),
        ('kersInput', c_float),
        ('autoShifterOn', c_int32),
        ('rideHeight', c_float * 2),
    ]

class SPageFileGraphic(Structure):
    _pack_ = 4
    _fields_ = [
        ('packetId', c_int32),
        ('status', c_int32),
        ('session', c_int32),
        ('currentTime', c_wchar * 15),
        ('lastTime', c_wchar * 15),
        ('bestTime', c_wchar * 15),
        ('split', c_wchar * 15),
        ('completedLaps', c_int32),
        ('position', c_int32),
        ('iCurrentTime', c_int32),
        ('iLastTime', c_int32),
        ('iBestTime', c_int32),
        ('sessionTimeLeft', c_float),
        ('distanceTraveled', c_float),
        ('isInPit', c_int32),
        ('currentSectorIndex', c_int32),
        ('lastSectorTime', c_int32),
        ('numberOfLaps', c_int32),
        ('tyreCompound', c_wchar * 33),
        ('replayTimeMultiplier', c_float),
        ('normalizedCarPosition', c_float),
        ('carCoordinates', c_float * 3),
        ('penaltyTime', c_float),
        ('flag', c_int32),
        ('idealLineOn', c_int32),
    ]

class SPageFileStatic(Structure):
    _pack_ = 4
    _fields_ = [
        ('smVersion', c_wchar * 15),
        ('acVersion', c_wchar * 15),
        ('numberOfSessions', c_int32),
        ('numCars', c_int32),
        ('carModel', c_wchar * 33),
        ('track', c_wchar * 33),
        ('playerName', c_wchar * 33),
        ('playerSurname', c_wchar * 33),
        ('playerNick', c_wchar * 33),
        ('sectorCount', c_int32),
        ('maxTorque', c_float),
        ('maxPower', c_float),
        ('maxRpm', c_int32),
        ('maxFuel', c_float),
        ('suspensionMaxTravel', c_float * 4),
        ('tyreRadius', c_float * 4),
    ]

class SimInfo:
    def __init__(self):
        self.physics = None
        self.graphics = None
        self.static = None
        try:
            self._physics = mmap.mmap(-1, ctypes.sizeof(SPageFilePhysics), 'acpmf_physics')
            self._graphics = mmap.mmap(-1, ctypes.sizeof(SPageFileGraphic), 'acpmf_graphics')
            self._static = mmap.mmap(-1, ctypes.sizeof(SPageFileStatic), 'acpmf_static')

            self.physics = SPageFilePhysics.from_buffer(self._physics)
            self.graphics = SPageFileGraphic.from_buffer(self._graphics)
            self.static = SPageFileStatic.from_buffer(self._static)
        except Exception:
            pass # AC not running

    def close(self):
        for m in (getattr(self, attr, None) for attr in ['_physics', '_graphics', '_static']):
            if m:
                try:
                    m.close()
                except:
                    pass
info = SimInfo()

pygame.init()

os.environ['SDL_VIDEO_WINDOW_POS'] = dash_position
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
if fullscreen == True:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)

pygame.display.set_caption('Rallye Dashboard')
font_super_large = pygame.font.SysFont('arial', 300, bold=True)
font_large = pygame.font.SysFont('arial', 120, bold=True)
font_medium_large = pygame.font.SysFont('arial', 85, bold=True)
font_medium = pygame.font.SysFont('arial', 60, bold=True)
font_medium_small = pygame.font.SysFont('arial', 35, bold=True)
font_small = pygame.font.SysFont('arial', 20, bold=True)

def format_time(ms):
    if ms <= 0:
        return '--:--.---'
    minutes = ms // 60000
    seconds = (ms // 1000) % 60
    millis = ms % 1000
    return f'{minutes}:{seconds:02}.{millis:03}'

def format_delta(ms):
    if ms == 0:
        return '+0.000'
    sign = '+' if ms > 0 else '-'
    abs_ms = abs(ms)
    minutes = abs_ms // 60000
    seconds = (abs_ms // 1000) % 60 
    millis = abs_ms % 1000 
    if minutes > 0:
        return f'{sign}{minutes}:{seconds:02}.{millis:03}'
    else:
        return f'{sign}{seconds}.{millis:03}'

#Tach Settings
TACH_HEIGHT = 80 
TACH_Y = SCREEN_HEIGHT - TACH_HEIGHT
TACH_X = 0 
TACH_WIDTH = SCREEN_WIDTH 

def get_rpm_color(rpm_ratio):
    if rpm_ratio < 0.7:
        g = 255
        r = int(255 * (rpm_ratio / 0.7))
        b = 0 
    elif rpm_ratio < 0.9:
        r = 255
        g = int(255 * (1 - (rpm_ratio - 0.7) / 0.325))
        b = 0 
    else:
        r = 255
        g = int(100 * (1 - (rpm_ratio - 0.9) / 0.1))
        b = 0 
    return (r, g, b)

def find_max_rpm(static_max_rpm, current_rpm, max_seen_rpm):
    if static_max_rpm > 0:
        return static_max_rpm
    else:
        max_seen_rpm[0] = max(max_seen_rpm[0], current_rpm)
        return int(max_seen_rpm[0])

running = True
clock = pygame.time.Clock()
last_packet_id = -1

# Default Values
speed = rpm = throttle = brake = current_lap_ms = 0 
gear = 0 
max_rpm_seen = [0] 
distance_km = 0.0 
progress_percent = 0
speed_unit = 'KPH'
dist_units = 'KM'

previous_distance = 0.0
previous_time = 0 
delta_ms = 0 
delta_valid = False

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 0, 0))

    if info.physics and info.graphics:
        if info.physics.packetId != last_packet_id:
            last_packet_id = info.physics.packetId

            speed = info.physics.speedKmh
            rpm = info.physics.rpms
            gear = info.physics.gear - 1
            throttle = info.physics.gas
            brake = info.physics.brake
            current_lap_ms = info.graphics.iCurrentTime
            best_lap_ms = info.graphics.iBestTime
            distance_km = info.graphics.distanceTraveled / 1000.0
            max_rpm = find_max_rpm(info.static.maxRpm, rpm, max_rpm_seen)
            tc_level = info.physics.tc 
            abs_level = info.physics.abs
            engine_dmg = info.physics.carDamage[0] * 100
            tyre_wear_avg = sum(info.physics.tyreWear) / 4
            susp_dmg_max = max(info.physics.carDamage[2:5]) * 100
            tyre_punctrues = info.physics.numberOfTyresOut 

            # Calc is short for calculator
            progress_percent = info.graphics.normalizedCarPosition * 100.0 if info.graphics.normalizedCarPosition >= 0 else 0 
            
            if best_lap_ms > 0 and current_lap_ms > 0:
                expected_ms = best_lap_ms * info.graphics.normalizedCarPosition
                current_elapsed = current_lap_ms
                delta_ms = int(current_elapsed - expected_ms)
                delta_valid = True 
            else:
                delta_ms = 0 
                delta_valid = False


            if best_lap_ms > 0 and progress_percent > 1:
                pace_factor = current_lap_ms / (best_lap_ms * (progress_percent / 100.0))
                estimated_stage_ms = int(best_lap_ms * pace_factor)
            else:
                estimated_stage_ms = 0

            

        rpm_ratio = max(0, min(1, rpm / max(100, max_rpm)))

        # Rendering
        # Speed
        if freedom_units == True:
            speed = speed / 1.609
            speed_unit = 'MPH'
        speed_text = font_large.render(f'{int(speed)}', True, (255, 255, 255))
        screen.blit(speed_text, (10, 255))
        screen.blit(font_medium_small.render(speed_unit, True, (200, 200, 200)), (20 + speed_text.get_width(), 305))

        # RPM 
        rpm_text = font_large.render(f'{int(rpm)}', True, (255, 255, 255))
        screen.blit(rpm_text, (10, 380))
        screen.blit(font_medium_small.render('RPM', True, (200, 200, 200)), (20 + rpm_text.get_width(), 430))

        # Gear 
        flash_color = (255, 0, 0) if (pygame.time.get_ticks() // 75) % 2 else (255, 255, 255)
        gear_str = 'R' if gear == -1 else 'N' if gear == 0 else str(gear)
        gear_color = (255, 0, 0) if gear == -1 else flash_color if rpm_ratio > 0.95 else (255, 255, 255)
        gear_text = font_super_large.render(gear_str, True, gear_color)
        screen.blit(gear_text, ((SCREEN_WIDTH // 2 - gear_text.get_width() // 2), (SCREEN_HEIGHT // 2 - 75)))

        #RIGHT HAND SIDE PANEL
        right_x = SCREEN_WIDTH - 10

        # Times
        current_text = font_medium_large.render(format_time(current_lap_ms), True, (255, 255, 255))
        screen.blit(current_text, (right_x - current_text.get_width(), 280))
        screen.blit(font_small.render("CURRENT STAGE", True, (200, 200, 200)), (right_x - 250, 260))
        
        if delta_valid:
            delta_color = (0, 255, 0) if delta_ms < 0 else (255, 255, 0) if delta_ms == 0 else (255, 100, 100)
            delta_text = font_medium_large.render(format_delta(delta_ms), True, delta_color)
        else:
            delta_text = font_medium_large.render('+--.---', True, (150, 150, 150))
        screen.blit(delta_text, (SCREEN_WIDTH // 2 - delta_text.get_width() // 2, 180))

        if estimated_stage_ms > 0:
            est_text = font_medium_large.render(format_time(estimated_stage_ms), True, (100, 200, 255))
        else:
            est_text = font_medium_large.render('--:--.---', True, (100, 200, 255))
        screen.blit(est_text, (right_x - est_text.get_width(), 400))
        screen.blit(font_small.render('ESTIMATED STAGE', True, (100, 200, 255)), (right_x - 250, 380))

        # Stage progress 
        if freedom_units == True:
            dist_units = 'Mi'
            distance_km = distance_km / 1.609
                
        progress_text = font_medium_small.render(f'{distance_km:.2f} {dist_units}', True, (255, 255, 255))
        screen.blit(progress_text, (right_x - progress_text.get_width(), 150))

        # Progress Bar 
        bar_width = SCREEN_WIDTH - 30 - progress_text.get_width()
        bar_height = 10 
        bar_x = SCREEN_WIDTH - bar_width - 20 - progress_text.get_width()
        bar_y = 165
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        fill_width = int(bar_width * (progress_percent / 100.0))
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, fill_width, bar_height))
        percent_text = font_small.render(f'{progress_percent:.0f}%', True, (200, 200, 200))
        screen.blit(percent_text, (fill_width, bar_y - 25))

        # Input Pos Bars
        pygame.draw.rect(screen, (0, 255, 0), (620, 500 - int(throttle * 220), 10, int(throttle * 220)))
        pygame.draw.rect(screen, (255, 0, 0), (400, 500 - int(brake * 220), 10, int(brake * 220)))

        #RPM bar 
        fill_width = int(TACH_WIDTH * rpm_ratio)

        pygame.draw.rect(screen, (30, 30, 30), (TACH_X, TACH_Y, TACH_WIDTH, TACH_HEIGHT))
        if fill_width > 0:
            for x in range(TACH_X, TACH_X + fill_width):
                segment_ratio = (x - TACH_X) / TACH_WIDTH
                color = get_rpm_color(segment_ratio)
                pygame.draw.line(screen, color, (x, TACH_Y), (x, TACH_Y + TACH_HEIGHT - 1), 1)

        #TC and abs
        if tc_level < 0.1:
            tc_color = (0, 255, 0)
            tc_text_str = 'TC OFF'
        elif tc_level < 0.5:
            tc_color = (255, 200, 0)
            tc_text_str = 'TC'
        else:
            tc_color(255, 0, 0)
            tc_text_str = 'TC !'
        tc_indicator = font_medium.render(tc_text_str, True, tc_color)
        screen.blit(tc_indicator, (10, 10))

        if abs_level < 0.1:
            abs_color = (0, 255, 0)
            abs_text_str = 'ABS OFF'
        else:
            abs_color = (255, 0, 0)
            abs_text_str = 'ABS !'

        abs_indicator = font_medium.render(abs_text_str, True, abs_color)
        screen.blit(abs_indicator, (10, 70))

        # Engine Damage 
        dmg_bar_x = right_x - 350
        dmg_bar_y = 20 
        pygame.draw.rect(screen, (40, 40, 40), (dmg_bar_x, dmg_bar_y, 350, 30))
        eng_fill_w = int(350 * (engine_dmg / 100))
        if eng_fill_w > 0:
            pygame.draw.rect(screen, (255, 0, 0), (dmg_bar_x, dmg_bar_y, eng_fill_w, 30))
        eng_pct = font_small.render(f'ENG {engine_dmg:.0f}%', True, (255, 0, 0))
        screen.blit(eng_pct, (dmg_bar_x - eng_pct.get_width() - 10, dmg_bar_y))

        # Tires bar
        tyre_bar_y = dmg_bar_y + 35 
        pygame.draw.rect(screen, (40, 40, 40), (dmg_bar_x, tyre_bar_y, 350, 30))
        tyre_fill_w = int(350 * (tyre_wear_avg / 100))
        tyre_color = (255, 165, 0) if tyre_punctrues == 0 else (255, 100, 0)
        if tyre_fill_w > 0:
            pygame.draw.rect(screen, tyre_color, (dmg_bar_x, tyre_bar_y, tyre_fill_w, 30))
        punc_text = '!' * tyre_punctrues
        tyre_pct = font_small.render(f'TIRE {tyre_wear_avg:.0f}% {punc_text}', True, (255, 200, 10))
        screen.blit(tyre_pct, (dmg_bar_x - tyre_pct.get_width() - 10, tyre_bar_y))

        susp_bar_y = tyre_bar_y + 35 
        pygame.draw.rect(screen, (40, 40, 40), (dmg_bar_x, susp_bar_y, 350, 30))
        susp_fill_w = int(350 * (susp_dmg_max / 100))
        if susp_fill_w > 0:
            pygame.draw.rect(screen, (100, 150, 255), (dmg_bar_x, susp_bar_y, susp_fill_w, 30))
        susp_pct = font_small.render(f'SUSP {susp_dmg_max:.0f}%', True, (150, 200, 255))
        screen.blit(susp_pct, (dmg_bar_x - susp_pct.get_width() - 10, susp_bar_y))

    else:
        # AC not running - just shows zeros or a standby message
        screen.blit(font_large.render("0", True, (100, 100, 100)), (50, 50))
        screen.blit(font_large.render("0", True, (100, 100, 100)), (300, 50))
        screen.blit(font_large.render("N", True, (100, 100, 100)), (600, 50))

    pygame.display.flip()
    clock.tick(refresh_rate) # Hz Refresh rate, AC physics is slower than 144Hz

info.close()
pygame.quit()


