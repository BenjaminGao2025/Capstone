import os
file_path = '/hy-tmp/vllm-ltr/vllm/core/scheduler.py'
with open(file_path, 'r') as f:
    content = f.read()

old_key = '''        def _key(req):
            nonlocal n_aged
            is_waiting = id(req) in waiting_ids
            waited = now - req.metrics.arrival_time
            if is_waiting and waited >= aging_s:
                n_aged += 1
                # Tier 0: aged → FCFS by arrival time
                return (0, req.metrics.arrival_time, 0.0)
            elif preempt_protect:
                if not is_waiting:
                    # Tier 1: running/swapped → highest aux_model_score first
                    return (1, 0.0, -req.aux_model_score)
                else:
                    # Tier 2: normal waiting → highest aux_model_score first
                    return (2, 0.0, -req.aux_model_score)
            else:
                # Tier 1: normal LTR → highest aux_model_score first
                return (1, 0.0, -req.aux_model_score)'''

new_key = '''        def _key(req):
            nonlocal n_aged
            is_waiting = id(req) in waiting_ids
            waited = now - req.metrics.arrival_time
            
            if preempt_protect and not is_waiting:
                # Absolute highest priority: protect running/swapped from being preempted by any waiting request
                return (-1, 0.0, -req.aux_model_score)
                
            if is_waiting and waited >= aging_s:
                n_aged += 1
                # Tier 0: aged waiting → FCFS by arrival time
                return (0, req.metrics.arrival_time, 0.0)
            else:
                # Tier 1: normal LTR (or running/swapped if protect=0) → highest aux_model_score first
                return (1, 0.0, -req.aux_model_score)'''

content = content.replace(old_key, new_key)
with open(file_path, 'w') as f:
    f.write(content)
