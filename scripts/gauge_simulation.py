from datetime import datetime

print("=" * 55)
print("FLOODSENSE - RIVER GAUGE SIMULATION")
print("=" * 55)

print("\nEnter two river-level readings.")
print("Use metres and ensure both readings use the same gauge datum.")

while True:
    try:
        previous_level = float(input("\nPrevious river level (m): "))
        current_level = float(input("Current river level (m): "))
        elapsed_minutes = float(input("Minutes between readings: "))

        if previous_level < 0 or current_level < 0:
            print("River levels cannot be negative in this simulation.")
            continue

        if elapsed_minutes <= 0:
            print("The time interval must be greater than zero.")
            continue

        break

    except ValueError:
        print("Please enter valid numerical values.")

change = current_level - previous_level
rate_per_hour = change / elapsed_minutes * 60

# Demonstration threshold only; calibrate using actual gauge characteristics.
stable_threshold = 0.02

if change > stable_threshold:
    trend = "RISING"
elif change < -stable_threshold:
    trend = "FALLING"
else:
    trend = "STABLE"

print("\n" + "=" * 55)
print("RIVER GAUGE RESULTS")
print("=" * 55)

print(f"Previous level: {previous_level:.2f} m")
print(f"Current level:  {current_level:.2f} m")
print(f"Level change:   {change:+.3f} m")
print(f"Change rate:    {rate_per_hour:+.3f} m/hour")
print(f"Detected trend: {trend}")

print("\n" + "=" * 55)
print("EVIDENCE-BASED INTERPRETATION")
print("=" * 55)

print("Satellite comparison:")
print("  Observation dates: 15 September and 14 October 2026")
print("  Net classified-area change: approximately +1.570 km^2")
print("  Relative classified-area change: +43.13%")
print("  Evidence status: historical classification change")

if trend == "RISING":
    print("\nAssessment: River level is rising.")
    print("Action: Continue monitoring and check official local warnings.")
    print("Satellite evidence is historical and cannot confirm current flood extent.")
elif trend == "FALLING":
    print("\nAssessment: River level is falling.")
    print("Action: Continue monitoring; a falling gauge does not prove that")
    print("previously inundated areas are safe.")
else:
    print("\nAssessment: River level is approximately stable.")
    print("Action: Continue monitoring and check official local warnings.")

print("\nThis is a demonstration, not a validated flood forecast.")
print("No flood-arrival time or confirmed affected-area boundary is inferred.")
