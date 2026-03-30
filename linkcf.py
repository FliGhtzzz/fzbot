import json
import random
import requests
import discord
file = open("link.json", "r")
link_data = json.load(file)
file.close()

def askforcf(dcname, cfhandle):

    url = "https://codeforces.com/api/user.info"
    params = {
        "handles": cfhandle
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data["status"] != "OK":
            return f"Error : data[{'comment'}]"

    except Exception as e:
        return  f"Error : {e}"
    
    for i in link_data:
        if link_data[i]["linked"] == True and link_data[i]["codeforces.handle"] == cfhandle:
            return "error : This Codeforces account is already linked."
        if link_data[i]["linked"] == True and link_data[i]["codeforces.handle"] != cfhandle:
            return "error : Another Codeforces account is already linked to this Discord account."
        if link_data[i]["linked"] == False and link_data[i]["codeforces.handle"] == cfhandle:
            return  f"error : This Codeforces account is already in the process of linking. Please submit code to the https://codeforces.com/problemset/problem/{link_data[i]['cfproblem_id']}/{link_data[i]['cfproblem_index']}  to verify your account."


    rand = random.randint(1000, 2000)
    cnt = random.choice(['A', 'B', 'C'])
    link_data[dcname] = {
        "dcname": dcname,
        "linked": False,
        "cfproblem_id": rand,        
        "cfproblem_index": cnt,      
        "codeforces.handle": cfhandle  
    }

    with open("link.json", "w") as file:
        json.dump(link_data, file, indent=4)

    return f"Submit any code to https://codeforces.com/problemset/problem/{rand}/{cnt} to verify your account."

def vertifycf(dcname): 
    
    for i in link_data:
        if link_data[i]["dcname"] == dcname and link_data[i]["linked"] == False:
            url = "https://codeforces.com/api/user.status?handle=" + link_data[i]["codeforces.handle"] + "&from=1&count=100"
            try:
                response = requests.get(url)
                data = response.json()
                for j in data["result"]:
                    if j["problem"]["contestId"] == link_data[i]["cfproblem_id"] and j["problem"]["index"] == link_data[i]["cfproblem_index"]:
                        link_data[i]["linked"] = True
                        with open("link.json", "w") as file:
                            json.dump(link_data, file, indent=4)
                        return "Your account has been successfully linked!"
                return "Verification failed. Please make sure to submit code to the specified problem."
            except:
                return "error : Failed to fetch user status."
               
        if link_data[i]["dcname"] == dcname and link_data[i]["linked"] == True:
            return "error : This Discord account is already linked to a Codeforces account."
    return "Use cnttocf command to link your Codeforces account first."
