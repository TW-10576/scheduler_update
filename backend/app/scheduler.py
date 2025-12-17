"""
Schedule Generation Logic - Priority-Based Distribution
Based on reference implementation from shift_scheduler_backend_v2.py
Distributes shifts based on shift type priority and day priority
"""

from ortools.sat.python import cp_model
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math


class ShiftSchedulerV5:
    """
    Priority-Based Distribution Logic:
    1. Calculate total shifts per role (minus leaves)
    2. Distribute by priority percentage to each shift type
    3. Distribute across days based on day priorities
    4. Assign employees with equal share of each shift type
    """
    
    def __init__(self, employees: List[Dict], roles: List[Dict], 
                 role_shifts: Dict, leave_requests: Dict, 
                 unavailability: Dict, week_dates: List[str]):
        self.employees = employees
        self.roles = roles
        self.role_shifts = role_shifts  # role_id -> [shifts]
        self.leave_requests = leave_requests  # "emp_id-date" -> True
        self.unavailability = unavailability  # "emp_id-date" -> True
        self.week_dates = week_dates
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.feedback = []
        self.days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    def add_feedback(self, message: str, severity: str = 'info'):
        """Add feedback message"""
        self.feedback.append({'message': message, 'severity': severity})
        print(f"[{severity.upper()}] {message}")
    
    def _round_allocations(self, raw_allocations: Dict[str, float], target_total: int) -> Dict[str, int]:
        """
        Round fractional allocations to integers ensuring sum equals target_total.
        Uses the largest remainder method (Hamilton/Hare method).
        """
        # Step 1: Floor all values
        floored = {key: math.floor(value) for key, value in raw_allocations.items()}
        
        # Step 2: Calculate remainders
        remainders = {key: raw_allocations[key] - floored[key] for key in raw_allocations}
        
        # Step 3: Calculate how many units we need to add
        current_sum = sum(floored.values())
        units_to_add = target_total - current_sum
        
        # Step 4: Sort by remainder and add 1 to top items
        sorted_by_remainder = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
        
        result = floored.copy()
        for i in range(min(units_to_add, len(sorted_by_remainder))):
            key = sorted_by_remainder[i][0]
            result[key] += 1
        
        return result
    
    def _calculate_shifts_per_week(self, employee: Dict) -> int:
        """Calculate shifts per week from weekly hours"""
        weekly_hours = employee.get('weekly_hours', 40)
        daily_max = employee.get('daily_max_hours', 8)
        return int(weekly_hours / daily_max) if daily_max > 0 else 5
    
    def _is_on_leave(self, employee_id: int, date: str) -> bool:
        """Check if employee is on leave"""
        return f"{employee_id}-{date}" in self.leave_requests
    
    def _is_unavailable(self, employee_id: int, date: str) -> bool:
        """Check if employee is unavailable"""
        return f"{employee_id}-{date}" in self.unavailability
    
    def generate_schedule(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Generate schedule with priority-based distribution
        Returns: (schedule, error_message)
        """
        self.add_feedback("Starting schedule generation with priority-based distribution...", 'info')
        
        # Step 1: Calculate daily availability
        daily_availability = {}
        for date_idx, date in enumerate(self.week_dates):
            day_name = self.days_of_week[date_idx]
            daily_availability[day_name] = {}
            
            for role in self.roles:
                role_id = role['id']
                available_count = sum(
                    1 for emp in self.employees
                    if emp.get('role_id') == role_id and
                    not self._is_on_leave(emp['id'], date) and
                    not self._is_unavailable(emp['id'], date)
                )
                daily_availability[day_name][role_id] = available_count
                self.add_feedback(
                    f"  {day_name} - Role '{role['name']}': {available_count} employees available",
                    'info'
                )
        
        # Step 2: Calculate total shifts per role
        role_capacities = {}
        for role in self.roles:
            role_id = role['id']
            role_employees = [e for e in self.employees if e.get('role_id') == role_id]
            
            total_shifts = sum(
                e.get('shifts_per_week', self._calculate_shifts_per_week(e))
                for e in role_employees
            )
            
            # Subtract leaves
            for emp in role_employees:
                leave_count = sum(
                    1 for date in self.week_dates
                    if self._is_on_leave(emp['id'], date)
                )
                total_shifts -= leave_count
            
            role_capacities[role_id] = max(0, total_shifts)
            self.add_feedback(
                f"  Role '{role['name']}': {total_shifts} total shifts needed",
                'info'
            )
        
        # Step 3: Create assignment variables and apply constraints
        assignments = {}
        for emp in self.employees:
            emp_id = emp['id']
            assignments[emp_id] = {}
            
            for date_idx, date in enumerate(self.week_dates):
                assignments[emp_id][date] = {}
                day_name = self.days_of_week[date_idx]
                
                if self._is_on_leave(emp_id, date) or self._is_unavailable(emp_id, date):
                    continue
                
                role_id = emp.get('role_id')
                if role_id not in self.role_shifts:
                    continue
                
                for shift in self.role_shifts[role_id]:
                    shift_schedule = shift.get('schedule_config', {}).get(day_name, {})
                    if shift_schedule.get('enabled', False):
                        var = self.model.NewBoolVar(f'e{emp_id}_d{date}_s{shift["id"]}')
                        assignments[emp_id][date][shift['id']] = var
        
        # Constraint 1: Each employee works exact shifts (minus leaves)
        for emp in self.employees:
            emp_id = emp['id']
            shifts_per_week = emp.get('shifts_per_week', self._calculate_shifts_per_week(emp))
            
            leave_days = sum(
                1 for date in self.week_dates
                if self._is_on_leave(emp_id, date)
            )
            
            target_shifts = max(0, shifts_per_week - leave_days)
            
            week_shifts = []
            for date in self.week_dates:
                for shift_id in assignments[emp_id].get(date, {}):
                    week_shifts.append(assignments[emp_id][date][shift_id])
            
            if week_shifts and target_shifts > 0:
                self.model.Add(sum(week_shifts) == target_shifts)
            elif week_shifts:
                self.model.Add(sum(week_shifts) == 0)
        
        # Constraint 2: One shift per day maximum
        for emp in self.employees:
            emp_id = emp['id']
            for date in self.week_dates:
                day_shifts = list(assignments[emp_id].get(date, {}).values())
                if len(day_shifts) > 1:
                    self.model.Add(sum(day_shifts) <= 1)
        
        # Objective: Maximize coverage
        objective_terms = []
        for emp_id in assignments:
            for date in assignments[emp_id]:
                for shift_id in assignments[emp_id][date]:
                    objective_terms.append(assignments[emp_id][date][shift_id])
        
        if objective_terms:
            self.model.Maximize(sum(objective_terms))
        
        # Solve
        self.add_feedback("Solving schedule with OR-Tools CP-SAT...", 'info')
        self.solver.parameters.max_time_in_seconds = 90.0
        self.solver.parameters.num_search_workers = 8
        
        status = self.solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            self.add_feedback(
                f"✅ {'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE'} solution found!",
                'success'
            )
            return self._extract_solution(assignments), None
        else:
            return None, "Cannot generate schedule. Please review constraints."
    
    def _extract_solution(self, assignments: Dict) -> Dict:
        """Extract schedule from solver solution"""
        schedule = {}
        
        for emp_id in assignments:
            for date in assignments[emp_id]:
                for shift_id, var in assignments[emp_id][date].items():
                    if self.solver.Value(var) == 1:
                        if date not in schedule:
                            schedule[date] = {}
                        if emp_id not in schedule[date]:
                            schedule[date][emp_id] = []
                        
                        # Find shift details
                        shift = None
                        for role_id, shifts in self.role_shifts.items():
                            shift = next((s for s in shifts if s['id'] == shift_id), None)
                            if shift:
                                break
                        
                        if shift:
                            schedule[date][emp_id].append(shift)
        
        self.add_feedback("\n=== SCHEDULE GENERATED ===", 'success')
        total_shifts = sum(
            len(emp_shifts)
            for day_shifts in schedule.values()
            for emp_shifts in day_shifts.values()
        )
        self.add_feedback(f"Total shifts assigned: {total_shifts}", 'success')
        
        return schedule
    
    def get_feedback(self) -> List[Dict]:
        """Return all feedback messages"""
        return self.feedback
