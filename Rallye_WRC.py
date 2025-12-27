import pygame
import socket
import json
import struct
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
dash_position = '100, 100'

# UDP Port (match your config.json)
UDP_PORT = 9999

# Telemetry Directory
telemetry_directory = r"~\Documents\My Games\WRC\telemetry\readme" 

# -----------------------------------------------------------------------------


# Dynamic UDP Parser for EA SPORTS WRC Native Telemetry
TELEMETRY_DIR = os.path.expanduser(telemetry_directory)
CHANNELS_JSON = os.path.join(TELEMETRY_DIR, "channels.json")
STRUCTURE_JSON = os.path.join(TELEMETRY_DIR, "udp", "wrc.json")

def load_udp_parser():
    with open(CHANNELS_JSON, 'r') as f:
        channels_data = json.load(f)
        channels = {ch['id']: ch for ch in channels_data['channels']}
    
    with open(STRUCTURE_JSON, 'r') as f:
        struct_data = json.load(f)
    
    # session_update packet
    packet = next(p for p in struct_data['packets'] if p['id'] == 'session_update')
    header = struct_data['header']['channels']
    update = packet['channels']
    all_channels = header + update
    
    type_map = {
        'boolean': '?',
        'uint8': 'B', 'int8': 'b',
        'uint16': 'H', 'int16': 'h',
        'uint32': 'I', 'int32': 'i',
        'uint64': 'Q', 'int64': 'q',
        'float32': 'f', 'float64': 'd',
    }
    
    fmt = '<' + ''.join(type_map[channels[ch]['type']] for ch in all_channels)
    return fmt, all_channels

unpack_fmt, channel_order = load_udp_parser()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", UDP_PORT))
sock.settimeout(0.01)  # Non-blocking

pygame.init()

os.environ['SDL_VIDEO_WINDOW_POS'] = dash_position
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
if fullscreen:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)

pygame.display.set_caption('EA WRC Rallye Dashboard')
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

# Default Values
speed = rpm = throttle = brake = current_lap_ms = 0 
gear = 0 
max_rpm_seen = [0] 
distance_km = 0.0 
progress_percent = 0
speed_unit = 'KPH'
dist_units = 'KM'

delta_ms = 0 
delta_valid = False
estimated_stage_ms = 0

data = {}

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 0, 0))

    # Receive UDP packet
    try:
        packet, _ = sock.recvfrom(4096)
        values = struct.unpack(unpack_fmt, packet)
        data = dict(zip(channel_order, values))
    except:
        pass  # No new packet

    if data:
        # === CHANNEL MAPPING (adjust these based on your channels.json) ===
        # Run once with print(data) to see exact names and update below
        speed = data.get('speed', 0)  # usually km/h
        rpm = data.get('rpm', 0) or data.get('engine_rpm', 0)
        gear = data.get('gear', 0)  # adjust offset if needed
        throttle = data.get('throttle', 0) or data.get('gas', 0)
        brake = data.get('brake', 0)
        current_lap_ms = data.get('stage_current_time', 0) * 1000 or data.get('current_time_ms', 0)  # ms
        best_lap_ms = data.get('stage_best_time', 0) * 1000 or data.get('best_time_ms', 0)
        progress_percent = data.get('normalized_spline_position', 0) * 100 or data.get('stage_progress', 0)
        distance_km = data.get('distance_completed', 0) / 1000 or data.get('distance_traveled', 0) / 1000
        max_rpm = find_max_rpm(data.get('max_rpm', 0), rpm, max_rpm_seen)

        tc_level = data.get('tc_intervention', 0) or 0
        abs_level = data.get('abs_intervention', 0) or 0
        engine_dmg = data.get('engine_damage', 0) * 100 or 0
        tyre_wear_avg = data.get('tyre_wear_average', 0) * 100 or sum(data.get('tyre_wear', [0]*4)) / 4 * 100
        susp_dmg_max = data.get('suspension_damage', 0) * 100 or 0
        tyre_punctures = data.get('flat_tyres', 0) or 0

        # Delta & Estimated
        if best_lap_ms > 0 and current_lap_ms > 0:
            expected_ms = best_lap_ms * (progress_percent / 100.0)
            delta_ms = int(current_lap_ms - expected_ms)
            delta_valid = True 
        else:
            delta_valid = False

        if best_lap_ms > 0 and progress_percent > 1:
            pace_factor = current_lap_ms / (best_lap_ms * (progress_percent / 100.0))
            estimated_stage_ms = int(best_lap_ms * pace_factor)
        else:
            estimated_stage_ms = 0

        rpm_ratio = max(0, min(1, rpm / max(100, max_rpm)))

        # Rendering (exact same as your AC code)
        if freedom_units:
            speed = speed / 1.609
            speed_unit = 'MPH'
            if 'Mi' in dist_units:
                distance_km = distance_km / 1.609
            dist_units = 'Mi'

        speed_text = font_large.render(f'{int(speed)}', True, (255, 255, 255))
        screen.blit(speed_text, (10, 255))
        screen.blit(font_medium_small.render(speed_unit, True, (200, 200, 200)), (20 + speed_text.get_width(), 305))

        rpm_text = font_large.render(f'{int(rpm)}', True, (255, 255, 255))
        screen.blit(rpm_text, (10, 380))
        screen.blit(font_medium_small.render('RPM', True, (200, 200, 200)), (20 + rpm_text.get_width(), 430))

        flash_color = (255, 0, 0) if (pygame.time.get_ticks() // 75) % 2 else (255, 255, 255)
        gear_str = 'R' if gear == -1 else 'N' if gear == 0 else str(gear)
        gear_color = (255, 0, 0) if gear == -1 else flash_color if rpm_ratio > 0.95 else (255, 255, 255)
        gear_text = font_super_large.render(gear_str, True, gear_color)
        screen.blit(gear_text, ((SCREEN_WIDTH // 2 - gear_text.get_width() // 2), (SCREEN_HEIGHT // 2 - 75)))

        right_x = SCREEN_WIDTH - 10

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

        progress_text = font_medium_small.render(f'{distance_km:.2f} {dist_units}', True, (255, 255, 255))
        screen.blit(progress_text, (right_x - progress_text.get_width(), 150))

        bar_width = SCREEN_WIDTH - 30 - progress_text.get_width()
        bar_x = SCREEN_WIDTH - bar_width - 20 - progress_text.get_width()
        bar_y = 165
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, 10))
        fill_width = int(bar_width * (progress_percent / 100.0))
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, fill_width, 10))
        percent_text = font_small.render(f'{progress_percent:.0f}%', True, (200, 200, 200))
        screen.blit(percent_text, (fill_width, bar_y - 25))

        pygame.draw.rect(screen, (0, 255, 0), (620, 500 - int(throttle * 220), 10, int(throttle * 220)))
        pygame.draw.rect(screen, (255, 0, 0), (400, 500 - int(brake * 220), 10, int(brake * 220)))

        fill_width = int(TACH_WIDTH * rpm_ratio)
        pygame.draw.rect(screen, (30, 30, 30), (TACH_X, TACH_Y, TACH_WIDTH, TACH_HEIGHT))
        if fill_width > 0:
            for x in range(TACH_X, TACH_X + fill_width):
                segment_ratio = (x - TACH_X) / TACH_WIDTH
                color = get_rpm_color(segment_ratio)
                pygame.draw.line(screen, color, (x, TACH_Y), (x, TACH_Y + TACH_HEIGHT - 1), 1)

        # TC and ABS
        if tc_level < 0.1:
            tc_color = (0, 255, 0)
            tc_text_str = 'TC OFF'
        elif tc_level < 0.5:
            tc_color = (255, 200, 0)
            tc_text_str = 'TC'
        else:
            tc_color = (255, 0, 0)
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

        # Damage bars
        dmg_bar_x = right_x - 350
        dmg_bar_y = 20 
        pygame.draw.rect(screen, (40, 40, 40), (dmg_bar_x, dmg_bar_y, 350, 30))
        eng_fill_w = int(350 * (engine_dmg / 100))
        if eng_fill_w > 0:
            pygame.draw.rect(screen, (255, 0, 0), (dmg_bar_x, dmg_bar_y, eng_fill_w, 30))
        eng_pct = font_small.render(f'ENG {engine_dmg:.0f}%', True, (255, 0, 0))
        screen.blit(eng_pct, (dmg_bar_x - eng_pct.get_width() - 10, dmg_bar_y))

        tyre_bar_y = dmg_bar_y + 35 
        pygame.draw.rect(screen, (40, 40, 40), (dmg_bar_x, tyre_bar_y, 350, 30))
        tyre_fill_w = int(350 * (tyre_wear_avg / 100))
        tyre_color = (255, 165, 0) if tyre_punctures == 0 else (255, 100, 0)
        if tyre_fill_w > 0:
            pygame.draw.rect(screen, tyre_color, (dmg_bar_x, tyre_bar_y, tyre_fill_w, 30))
        punc_text = '!' * tyre_punctures
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
        # Standby
        screen.blit(font_large.render("Waiting for EA WRC telemetry...", True, (100, 100, 100)), (SCREEN_WIDTH//2 - 300, SCREEN_HEIGHT//2))

    pygame.display.flip()
    clock.tick(refresh_rate)

sock.close()
pygame.quit()
