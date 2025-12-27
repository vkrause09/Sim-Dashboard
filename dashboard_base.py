import pygame
import ctypes
from ctypes import c_int32, c_float, c_wchar, Structure
import mmap
import os

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
        ('speedMph', c_float),
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
        # Add telemetry fields here
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
        # Add telemetry fields here
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
        # Add telemetry fields here
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

#-----------------------------------------------------------------------
# Set screen dimensions below
SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 600 

# Change to the position of your dash
# Ex: if your main monitor is 1920x1080 and Dash is set up to the right -> '1920, 0'
os.environ['SDL_VIDEO_WINDOW_POS'] = '0, 0'

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
# Uncomment the next line for fullscreen borderless on the dash screen
# screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
#-----------------------------------------------------------------------

pygame.display.set_caption('Rallye Dashboard')
font_large = pygame.font.SysFont('arial', 100, bold=True)
font_medium = pygame.font.SysFont('arial', 50)

def format_time(ms):
    if ms <= 0:
        return '--:--.---'
    minutes = ms // 60000
    seconds = (ms // 1000) % 60
    millis = ms % 1000
    return f'{minutes}:{seconds:02}.{millis:03}'

running = True
clock = pygame.time.Clock()
last_packet_id = -1

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 0, 0))

    if info.physics and info.graphics:
        if info.physics.packetId != last_packet_id:
            last_packet_id = info.physics.packetId

            speed = info.physics.speedMph
            rpm = info.physics.rpms
            gear = info.physics.gear - 1 if info.physics.gear > 1 else info.physics.gear
            throttle = info.physics.gas
            brake = info.physics.brake
            fuel = info.physics.fuel
            current_lap_ms = info.graphics.iCurrentTime
            best_lap_ms = info.graphics.iBestTime
            avg_tyre_wear = sum(info.physics.tyreWear) / 4 * 100
            max_fuel = info.static.maxFuel if info.static and info.static.maxFuel > 0 else 100
            # Add fields you want to display here or edit the ones above IDC
            print(info.physics.tyreWear)

        # Rendering
        # Speed
        speed_text = font_large.render(f'{int(speed)}', True, (255, 255, 255))
        screen.blit(speed_text, (50, 50))
        screen.blit(font_medium.render('Mph', True, (200, 200, 200)), (50, 160))

        # RPM 
        rpm_text = font_large.render(f'{int(rpm)}', True, (255, 255, 255))
        screen.blit(rpm_text, (300, 50))
        screen.blit(font_medium.render('RPM', True, (200, 200, 200)), (300, 160))

        # Gear 
        gear_str = 'R' if gear == -1 else 'N' if gear == 0 else str(gear)
        gear_color = (255, 0, 0) if gear == -1 else (0, 255, 0)
        gear_text = font_large.render(gear_str, True, gear_color)
        screen.blit(gear_text, (600, 50))

        # Lap Times
        screen.blit(font_medium.render(f"Current: {format_time(current_lap_ms)}", True, (255, 255, 255)), (50, 250))
        screen.blit(font_medium.render(f"Best: {format_time(best_lap_ms)}", True, (0, 255, 0)), (50, 320))

        # Fuel bar
        fuel_width = int((fuel / max_fuel) * 300) if max_fuel > 0 else 0
        pygame.draw.rect(screen, (0, 255, 255), (450, 250, fuel_width, 40))
        screen.blit(font_medium.render("FUEL", True, (200, 200, 200)), (450, 300))

        # Tyre wear bar
        pygame.draw.rect(screen, (255, 165, 0), (450, 350, int(avg_tyre_wear * 3), 30))
        screen.blit(font_medium.render(f"WEAR {avg_tyre_wear:.0f}%", True, (200, 200, 200)), (450, 390))

        # Throttle / Brake bars
        pygame.draw.rect(screen, (0, 255, 0), (50, 400, int(throttle * 400), 30))
        pygame.draw.rect(screen, (255, 0, 0), (50, 440, int(brake * 400), 30))

    else:
        # AC not running - just shows zeros or a standby message
        screen.blit(font_large.render("0", True, (100, 100, 100)), (50, 50))
        screen.blit(font_large.render("0", True, (100, 100, 100)), (300, 50))
        screen.blit(font_large.render("N", True, (100, 100, 100)), (600, 50))

    pygame.display.flip()
    clock.tick(144) # Hz Refresh rate, AC physics is slower than 144Hz

info.close()
pygame.quit()


































