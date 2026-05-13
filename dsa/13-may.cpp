#include<iostream>
#include<vector>
#include<unordered_set>
using namespace std;

int solve(int n, int target){
    long long S = (n*(n+1))/2;
    
    if(S < target || target<-S || (S-target)%2)      return vector<int>{};
    int rqd = (S-target)/2;
    int rem = min(rqd,n);

    set<int> s;
    vector<int>v;
    while(rqd){
        rqd-=rem;
        s.insert(rem);
        v.push_back(-rem);
        rem = min(rqd,rem-1);
    }
    for(int i=1;i<=n;i++){
        if(s.count(i))  continue;
        v.push_back(i);
    }
    return v;
}