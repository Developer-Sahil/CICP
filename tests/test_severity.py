"""
Comprehensive testing script for severity detection accuracy.
Tests various complaint scenarios to ensure correct severity classification.
"""

import sys
from ai.severity import detect_severity, explain_severity

# Test cases with expected severity levels
TEST_CASES = [
    # ============================================================================
    # HIGH SEVERITY - Medical Emergencies
    # ============================================================================
    {
        "complaint": "A student was hospitalized yesterday after eating mess food. They had severe food poisoning and needed emergency treatment.",
        "expected": "high",
        "category": "Medical Emergency - Hospitalization"
    },
    {
        "complaint": "My roommate collapsed in the hostel room and was taken to hospital by ambulance. This is very serious.",
        "expected": "high",
        "category": "Medical Emergency - Ambulance"
    },
    {
        "complaint": "Three students were admitted to the hospital with food poisoning after eating at the mess last night.",
        "expected": "high",
        "category": "Medical Emergency - Multiple Students"
    },
    {
        "complaint": "I got injured in the gym because the equipment was broken. Had to visit emergency room.",
        "expected": "high",
        "category": "Medical Emergency - Injury"
    },
    {
        "complaint": "Someone broke their leg on the stairs because there was water spill and no caution sign. They are in hospital now.",
        "expected": "high",
        "category": "Medical Emergency - Broken Bone"
    },
    
    # ============================================================================
    # HIGH SEVERITY - Safety Hazards
    # ============================================================================
    {
        "complaint": "There's an exposed electrical wire in our room. It's sparking and very dangerous. This is a safety hazard.",
        "expected": "high",
        "category": "Safety Hazard - Electrical"
    },
    {
        "complaint": "Smelling gas leak in the hostel corridor. This is urgent and dangerous for everyone.",
        "expected": "high",
        "category": "Safety Hazard - Gas Leak"
    },
    {
        "complaint": "The ceiling in our room has a large crack and looks like it might collapse. This is unsafe.",
        "expected": "high",
        "category": "Safety Hazard - Structural"
    },
    {
        "complaint": "Fire alarm went off but no one evacuated because they don't work properly. This is dangerous.",
        "expected": "high",
        "category": "Safety Hazard - Fire Safety"
    },
    
    # ============================================================================
    # HIGH SEVERITY - Severe Contamination
    # ============================================================================
    {
        "complaint": "Found maggots in the rice served at mess today. This is disgusting and a serious health hazard.",
        "expected": "high",
        "category": "Severe Contamination - Food"
    },
    {
        "complaint": "There was a cockroach in my food at the mess. Multiple students have found insects in their meals.",
        "expected": "high",
        "category": "Severe Contamination - Insects"
    },
    {
        "complaint": "The food served today was completely rotten and smelled terrible. Several students got sick after eating it.",
        "expected": "high",
        "category": "Severe Contamination - Spoiled Food"
    },
    {
        "complaint": "Raw sewage is backing up in our hostel bathroom. The smell is terrible and it's a health hazard.",
        "expected": "high",
        "category": "Severe Contamination - Sewage"
    },
    
    # ============================================================================
    # HIGH SEVERITY - Critical Service Failures
    # ============================================================================
    {
        "complaint": "No water in our hostel for 3 days now. Can't shower, flush toilets, or drink. This is urgent.",
        "expected": "high",
        "category": "Critical Failure - No Water"
    },
    {
        "complaint": "Power has been out for 2 days in extreme summer heat. Students are suffering without AC or fans.",
        "expected": "high",
        "category": "Critical Failure - No Power"
    },
    {
        "complaint": "No heating for a week during winter. Rooms are freezing and students are getting sick.",
        "expected": "high",
        "category": "Critical Failure - No Heating"
    },
    
    # ============================================================================
    # HIGH SEVERITY - Violence & Harassment
    # ============================================================================
    {
        "complaint": "I was harassed by a senior student. This has been ongoing and I feel threatened.",
        "expected": "high",
        "category": "Violence - Harassment"
    },
    {
        "complaint": "Witnessed a physical assault in the hostel last night. Someone needs to address this violence.",
        "expected": "high",
        "category": "Violence - Assault"
    },
    
    # ============================================================================
    # MEDIUM SEVERITY - Service Disruptions
    # ============================================================================
    {
        "complaint": "The WiFi has been very slow for the past week. Can't attend online classes properly.",
        "expected": "medium",
        "category": "Service Disruption - WiFi"
    },
    {
        "complaint": "AC in our room is not working. It's uncomfortable but manageable with fans.",
        "expected": "medium",
        "category": "Service Disruption - AC"
    },
    {
        "complaint": "Hot water is not available in the morning. We have to shower with cold water.",
        "expected": "medium",
        "category": "Service Disruption - Hot Water"
    },
    {
        "complaint": "The elevator has been broken for 2 weeks. Difficult for students on higher floors.",
        "expected": "medium",
        "category": "Service Disruption - Elevator"
    },
    
    # ============================================================================
    # MEDIUM SEVERITY - Quality Issues
    # ============================================================================
    {
        "complaint": "Mess food quality is poor. The food is often cold and doesn't taste good.",
        "expected": "medium",
        "category": "Quality Issue - Food"
    },
    {
        "complaint": "Bathroom cleaning is inadequate. Toilets are dirty and need better maintenance.",
        "expected": "medium",
        "category": "Quality Issue - Cleaning"
    },
    {
        "complaint": "Professor is often late to class and unprepared. Teaching quality is disappointing.",
        "expected": "medium",
        "category": "Quality Issue - Teaching"
    },
    
    # ============================================================================
    # MEDIUM SEVERITY - Repeated Issues
    # ============================================================================
    {
        "complaint": "Reported the broken door lock multiple times but nothing has been done. This is frustrating.",
        "expected": "medium",
        "category": "Repeated Issue - Ignored"
    },
    {
        "complaint": "Water leakage in bathroom continues despite reporting it twice. Needs attention.",
        "expected": "medium",
        "category": "Repeated Issue - Leakage"
    },
    
    # ============================================================================
    # LOW SEVERITY - Minor Issues & Suggestions
    # ============================================================================
    {
        "complaint": "Would be nice if the mess could add more vegetarian options to the menu.",
        "expected": "low",
        "category": "Suggestion - Menu"
    },
    {
        "complaint": "The library could use better lighting. Current lights are a bit dim.",
        "expected": "low",
        "category": "Minor Issue - Lighting"
    },
    {
        "complaint": "Suggestion: Add more study tables in the common area for students.",
        "expected": "low",
        "category": "Suggestion - Furniture"
    },
    {
        "complaint": "The paint in our room is old and could use refreshing. Just a cosmetic issue.",
        "expected": "low",
        "category": "Minor Issue - Aesthetic"
    },
    {
        "complaint": "Would appreciate if mess timings could be extended on weekends.",
        "expected": "low",
        "category": "Suggestion - Timing"
    },
]


def run_severity_tests():
    """
    Run all test cases and report results.
    """
    print("=" * 80)
    print("SEVERITY DETECTION ACCURACY TEST")
    print("=" * 80)
    print()
    
    total_tests = len(TEST_CASES)
    passed = 0
    failed = 0
    
    failures = []
    
    for i, test in enumerate(TEST_CASES, 1):
        complaint = test["complaint"]
        expected = test["expected"]
        category = test["category"]
        
        # Detect severity
        detected = detect_severity(complaint)
        
        # Check if correct
        is_correct = detected == expected
        
        if is_correct:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"
            failures.append({
                "test_num": i,
                "category": category,
                "expected": expected,
                "detected": detected,
                "complaint": complaint
            })
        
        print(f"Test {i:2d}/{total_tests} [{status}] - {category}")
        print(f"  Expected: {expected.upper():6s} | Detected: {detected.upper():6s}")
        
        if not is_correct:
            print(f"  Complaint: {complaint[:80]}...")
        
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed} ({passed/total_tests*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
    print()
    
    # Detailed failure report
    if failures:
        print("=" * 80)
        print("FAILED TEST DETAILS")
        print("=" * 80)
        print()
        
        for failure in failures:
            print(f"Test #{failure['test_num']}: {failure['category']}")
            print(f"  Expected: {failure['expected'].upper()}")
            print(f"  Detected: {failure['detected'].upper()}")
            print(f"  Complaint: {failure['complaint']}")
            
            # Get explanation
            explanation = explain_severity(failure['complaint'], failure['detected'])
            print(f"  Severity Score: {explanation['score']}")
            print(f"  Reasons: {', '.join(explanation['reasons'])}")
            print()
    
    # Return success status
    return failed == 0


def test_specific_complaint(complaint_text):
    """
    Test a specific complaint and show detailed analysis.
    """
    print("=" * 80)
    print("DETAILED SEVERITY ANALYSIS")
    print("=" * 80)
    print()
    print(f"Complaint: {complaint_text}")
    print()
    
    # Detect severity
    severity = detect_severity(complaint_text)
    
    # Get explanation
    explanation = explain_severity(complaint_text, severity)
    
    print(f"Detected Severity: {severity.upper()}")
    print(f"Severity Score: {explanation['score']}/10")
    print()
    print("Reasons:")
    for reason in explanation['reasons']:
        print(f"  • {reason}")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific complaint from command line
        complaint = " ".join(sys.argv[1:])
        test_specific_complaint(complaint)
    else:
        # Run all tests
        success = run_severity_tests()
        
        if success:
            print("🎉 All tests passed!")
            sys.exit(0)
        else:
            print("⚠️  Some tests failed. Please review the failures above.")
            sys.exit(1)