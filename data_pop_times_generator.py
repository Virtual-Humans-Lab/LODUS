import numpy as np
from collections import Counter
from pathlib import Path
import csv

#rng = np.random.default_rng(seed=0)

BASE_DIR = Path(__file__).resolve().parent

PLACES_CONFIG = {
    "marketplace": {
        "hours": list(range(7, 23)),  # 7 to 22
        "hours_sunday": list(range(7, 22)),  # 7 to 21
        "probabilities": {
            "seg": [0.016164, 0.026940, 0.038793, 0.048491, 0.054957, 0.057112, 0.057112, 0.061422, 0.070043, 0.081897, 0.094828, 0.102371, 0.100216, 0.086207, 0.063578, 0.039869],
            "ter": [0.017598, 0.028986, 0.040373, 0.050725, 0.055901, 0.056936, 0.055901, 0.060041, 0.068323, 0.080745, 0.093168, 0.099379, 0.097308, 0.085921, 0.066253, 0.042442],
            "qua": [0.020833, 0.035038, 0.048295, 0.058712, 0.062500, 0.063447, 0.062500, 0.065341, 0.072917, 0.082386, 0.090909, 0.093750, 0.087121, 0.071970, 0.052083, 0.032198],
            "qui": [0.019841, 0.031746, 0.043651, 0.052910, 0.056878, 0.056878, 0.056878, 0.060847, 0.068783, 0.079365, 0.091270, 0.097884, 0.095238, 0.083333, 0.063492, 0.041006],
            "sex": [0.018293, 0.029472, 0.040650, 0.049797, 0.054878, 0.056911, 0.058943, 0.063008, 0.071138, 0.082317, 0.092480, 0.097561, 0.094512, 0.083333, 0.064024, 0.042683],
            "sab": [0.015903, 0.028064, 0.043030, 0.055192, 0.062675, 0.063611, 0.062675, 0.064547, 0.071095, 0.080449, 0.087925, 0.093545, 0.090739, 0.079513, 0.060804, 0.040233],
            "dom": [0.012731, 0.026620, 0.043981, 0.060185, 0.071759, 0.072917, 0.068287, 0.067130, 0.071759, 0.082176, 0.090278, 0.096065, 0.094907, 0.082176, 0.059029],
        },
        "output_file": "data_input/popular_times/marketplace.csv",
    },
    "pharmacy": {
        "hours": list(range(8, 21)),  # 8 to 20
        "probabilities": {
            "seg": [0.045820, 0.055466, 0.053055, 0.050643, 0.060289, 0.068730, 0.073553, 0.079582, 0.089228, 0.105305, 0.120579, 0.108521, 0.089229],
            "ter": [0.050926, 0.071759, 0.081019, 0.074074, 0.074074, 0.071759, 0.071759, 0.071759, 0.086806, 0.086806, 0.096065, 0.089120, 0.074074],
            "qua": [0.042683, 0.071951, 0.078049, 0.080488, 0.075610, 0.069512, 0.064634, 0.069512, 0.071951, 0.087805, 0.101220, 0.098780, 0.087805],
            "qui": [0.064611, 0.061674, 0.054332, 0.048458, 0.051395, 0.061674, 0.074890, 0.102790, 0.099853, 0.102790, 0.099853, 0.093979, 0.083701],
            "sex": [0.036943, 0.056051, 0.077707, 0.089172, 0.075159, 0.075159, 0.072611, 0.084076, 0.094268, 0.095541, 0.091720, 0.084076, 0.067517],
            "sab": [0.070175, 0.080409, 0.074561, 0.080409, 0.083333, 0.083333, 0.089181, 0.077485, 0.073099, 0.054094, 0.070175, 0.077485, 0.086261],
        },
        "output_file": "data_input/popular_times/pharmacy.csv",
    },
    "restaurant": {
        "hours": list(range(11, 23)),  # 11 to 22
        "hours_sunday": list(range(11, 15)),  # 11 to 14
        "probabilities": {
            "seg": [0.071520, 0.111111, 0.109834, 0.088123, 0.065134, 0.052363, 0.060026, 0.072797, 0.090677, 0.102171, 0.099617, 0.076627],
            "ter": [0.082895, 0.125000, 0.121053, 0.092105, 0.067105, 0.060526, 0.064474, 0.073684, 0.085526, 0.089474, 0.077632, 0.060526],
            "qua": [0.078035, 0.122832, 0.130058, 0.101156, 0.075145, 0.060694, 0.062139, 0.069364, 0.082370, 0.085260, 0.075145, 0.057802],
            "qui": [0.069016, 0.107195, 0.104258, 0.082232, 0.057269, 0.049927, 0.057269, 0.080764, 0.099853, 0.113069, 0.101322, 0.077826],
            "sex": [0.058017, 0.094937, 0.104430, 0.084388, 0.064346, 0.060127, 0.068565, 0.087553, 0.100211, 0.105485, 0.097046, 0.074895],
            "sab": [0.058663, 0.105048, 0.133697, 0.121419, 0.095498, 0.068213, 0.054570, 0.055935, 0.068213, 0.084584, 0.085948, 0.068212],
            "dom": [0.150862, 0.258621, 0.314655, 0.275862],
        },
        "output_file": "data_input/popular_times/restaurant.csv",
    },
}

WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sab"]


def generate_popular_times(place: str, sample_size: int = 1000) -> None:
    """Generate popular times data for a given place and write to CSV.
    
    Args:
        place: Name of the place (marketplace, pharmacy, restaurant)
        sample_size: Number of samples to draw for each weekday (default: 1000)
    """
    place_lower = place.lower()
    
    if place_lower not in PLACES_CONFIG:
        raise ValueError(f"Local inválido: {place}. Opções: {list(PLACES_CONFIG.keys())}")
    
    config = PLACES_CONFIG[place_lower]
    probs = config["probabilities"]
    rng = np.random.default_rng(seed=0)
    #rng = np.random.default_rng() # Descomente essa linha e comente a de cima para voltar a mudar os csv.
    
    # Sample from probabilities for each weekday
    samples = {}
    for day in WEEKDAYS:
        hours_range = config["hours"]
        prob_list = probs[day]
        samples[day] = rng.choice(hours_range, size=sample_size, p=prob_list)
    
    # Special handling for Sunday if it exists
    if "dom" in probs:
        hours_sunday = config.get("hours_sunday", config["hours"])
        samples["dom"] = rng.choice(hours_sunday, size=sample_size, p=probs["dom"])
    
    
    counts = {day: Counter(samples[day]) for day in samples}
    
    output_file = BASE_DIR / config["output_file"]
    hours_range = config["hours"]
    hours_sunday = config.get("hours_sunday", config["hours"])
    ciclo = 0
    
    with open(output_file, "w", newline="", encoding="utf8") as f:
        writer = csv.writer(f)
        writer.writerow(["ciclo", "hora", "quantidade"])  

        #for hour in hours_range:
            #quantity = counts["seg"].get(hour, 0) # Only monday (for now)
            #writer.writerow([ciclo, hour, quantity])
        
        for day in WEEKDAYS:      # Maybe including the number of cicles, to simulate 7 days
           for hour in hours_range:
                quantity = counts[day].get(hour, 0)
                writer.writerow([ciclo, hour, quantity])
           ciclo = ciclo + 1
        
        if "dom" in probs:
            for hour in hours_sunday:
                quantity = counts["dom"].get(hour, 0)
                writer.writerow([ciclo, hour, quantity])
    
    #Used for debugging
    #print(f"Popular times data generated for '{place}' (sample size: {sample_size})")
    #print(f"CSV file saved: {output_file}")


if __name__ == "__main__":
    place = "restaurant"
    sample_size = 1000  
    
    try:
        generate_popular_times(place, sample_size)
    except ValueError as e:
        print(f"Error: {e}")

