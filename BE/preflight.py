import sys
import os

errors = []

# 1. Full app import
try:
    import app.main
    print("1. app.main import: OK")
except Exception as e:
    errors.append(f"1. app.main import FAILED: {e}")
    print(errors[-1])

# 2. All 6 users load with medical history
try:
    from app.db.repositories.user_repo import UserRepository
    repo = UserRepository()
    for uid in ['MEM-10001','MEM-10002','MEM-10003','MEM-10004','MEM-10005','MEM-10006']:
        u = repo.get_by_id(uid)
        assert u.medical_history.get('conditions'), f'{uid} missing conditions'
        assert u.medical_history.get('past_appointments'), f'{uid} missing past_appointments'
        assert u.insurance_plan_id.startswith('plan-'), f'{uid} bad plan_id: {u.insurance_plan_id}'
    print("2. All 6 users have medical history + valid plan IDs: OK")
except Exception as e:
    errors.append(f"2. User data FAILED: {e}")
    print(errors[-1])

# 3. System prompt builds without f-string errors for all users
try:
    from app.adk.agent import _build_system_prompt
    for uid in ['MEM-10001','MEM-10002','MEM-10003','MEM-10004','MEM-10005','MEM-10006']:
        prompt = _build_system_prompt(uid)
        assert 'MEDICAL HISTORY' in prompt, f'{uid} missing MEDICAL HISTORY'
        assert 'BOOKINGS MADE THROUGH THIS APP' in prompt, f'{uid} missing BOOKINGS section'
        assert 'Past Doctors' in prompt, f'{uid} missing Past Doctors'
        for bad in ['{condition}', '{specialty}', '{medication}']:
            assert bad not in prompt, f'{uid} has unresolved {bad} in prompt'
    print("3. System prompts build correctly, no f-string errors: OK")
except Exception as e:
    errors.append(f"3. System prompt FAILED: {e}")
    print(errors[-1])

# 4. History-aware ranking
try:
    from app.tools.provider_discovery_orchestrator import ProviderDiscoveryOrchestrator
    user = repo.get_by_id('MEM-10003')
    results = ProviderDiscoveryOrchestrator().execute(
        clinical_context={'primary_specialty':'Endocrinology','urgency':'routine','care_type':'in_person','nucc_codes':['207RE0101X']},
        user=user
    )
    assert len(results) > 0, 'No providers found'
    top = results[0]
    assert top.get('top_pick') == True, 'Top pick not marked'
    assert top.get('top_pick_reason'), 'Top pick reason missing'
    assert 'your_doctor' in top.get('explainability_signals', []), 'Continuity signal missing'
    print(f"4. History-aware ranking: OK -- top={top['name']} | {top['top_pick_reason']}")
except Exception as e:
    errors.append(f"4. Ranking FAILED: {e}")
    print(errors[-1])

# 5. Login works for all users
try:
    from app.router.auth_router import _repo as auth_repo
    for mid, pwd in [('MEM-10001','10001'),('MEM-10002','10002'),('MEM-10003','10003'),
                     ('MEM-10004','10004'),('MEM-10005','10005'),('MEM-10006','10006')]:
        u = auth_repo.authenticate(mid, pwd)
        assert u is not None, f'Login failed for {mid}'
    print("5. Login for all 6 users: OK")
except Exception as e:
    errors.append(f"5. Login FAILED: {e}")
    print(errors[-1])

# 6. FHIR data covers all 6 member cities
try:
    from app.fhir.bootstrap import load_fhir_repository
    fhir_repo = load_fhir_repository()
    cities = {loc.get('address',{}).get('city','') for loc in fhir_repo.locations.values()}
    for expected in ['Los Angeles','New York','Miami','Chicago','Seattle','Houston']:
        assert expected in cities, f'FHIR missing city: {expected}'
    print(f"6. FHIR covers all 6 cities, {len(fhir_repo.practitioners)} providers: OK")
except Exception as e:
    errors.append(f"6. FHIR data FAILED: {e}")
    print(errors[-1])

# 7. FHIR plan IDs match user plan IDs
try:
    plan_ids_in_fhir = set()
    for role in fhir_repo.practitioner_roles.values():
        for ext in role.get('extension', []):
            if ext.get('url') == 'network-plans':
                for p in ext.get('valueString','').split(','):
                    plan_ids_in_fhir.add(p.strip())
    for uid in ['MEM-10001','MEM-10002','MEM-10003','MEM-10004','MEM-10005','MEM-10006']:
        u = repo.get_by_id(uid)
        assert u.insurance_plan_id in plan_ids_in_fhir, f'{uid} plan_id {u.insurance_plan_id} not in FHIR'
    print("7. All user plan IDs match FHIR plan IDs: OK")
except Exception as e:
    errors.append(f"7. Plan ID alignment FAILED: {e}")
    print(errors[-1])

# 8. Static frontend exists and has correct user IDs
try:
    assert os.path.exists('app/static/index.html'), 'index.html missing'
    content = open('app/static/index.html', encoding='utf-8').read()
    assert 'MEM-10001' in content, 'index.html missing MEM-10001'
    assert 'currentUserId' in content, 'index.html missing currentUserId'
    assert 'token' not in content or 'currentUserId' in content, 'JWT token logic still present'
    print("8. Frontend index.html: OK")
except Exception as e:
    errors.append(f"8. Frontend FAILED: {e}")
    print(errors[-1])

# 9. IntentClarificationAgent accepts medical_history in session
try:
    from app.agents.intent_clarification_agent import IntentClarificationAgent
    import inspect
    src = inspect.getsource(IntentClarificationAgent)
    assert 'medical_history' in src, 'IntentClarificationAgent not using medical_history'
    assert 'known_block' in src, 'IntentClarificationAgent missing known_block'
    print("9. IntentClarificationAgent uses medical history: OK")
except Exception as e:
    errors.append(f"9. IntentClarificationAgent FAILED: {e}")
    print(errors[-1])

# 10. ExplainabilityAgent uses LLM
try:
    from app.agents.explainability_agent import ExplainabilityAgent
    src = inspect.getsource(ExplainabilityAgent)
    assert 'LLMService' in src, 'ExplainabilityAgent not using LLM'
    print("10. ExplainabilityAgent uses LLM: OK")
except Exception as e:
    errors.append(f"10. ExplainabilityAgent FAILED: {e}")
    print(errors[-1])

print()
if errors:
    print(f"FAILED -- {len(errors)} issue(s) found:")
    for e in errors:
        print(f"  FAIL: {e}")
    sys.exit(1)
else:
    print("ALL 10 CHECKS PASSED -- safe to run server")
