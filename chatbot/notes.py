

if "general" in choice:
    scenario["brand"] ='Basic' 
elif "lulu" in choice:
    scenario['brand']='Lulu'
else:
    scenario['brand']='Basic'
if "lowf" in choice:
    scenario['feel_level'] = 'Low'
elif "highf" in choice:
    scenario['feel_level'] = 'High'
if "lowt" in choice:
    scenario['think_level'] = 'Low'
elif "hight" in choice:
    scenario['think_level'] = 'High'