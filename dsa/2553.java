class Solution {
    public int[] separateDigits(int[] nums) {
        ArrayList<int> list = new ArrayList<>();
        for(int x: nums) {
            ArrayList<int> temp = new ArrayList<>();
            while(x) {
                temp.add(x%10);
                x /= 10;
            }
            for(int j=list.size()-1; i>=0; i--){
                list.add(temp[j]);
            }
        }
        return list;
    }

    static void main() {
        Solution s = new Solution();
        System.out.println(s.separateDigits(new int[]{1,2,3,4,5,6,7,8,9}));
    }
}