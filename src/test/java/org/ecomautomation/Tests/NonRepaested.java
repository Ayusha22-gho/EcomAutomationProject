package org.ecomautomation.Tests;

import net.bytebuddy.description.type.TypeList;

import java.util.HashMap;
import java.util.Map;

public class NonRepaested {

    public static Character NonRepeatedCharacter(String str){

        Map<Character , Integer> map = new HashMap<>();
        for (char ch : str.toCharArray()){
            map.put(ch, map.getOrDefault(ch,0)+1);
        }

        for(Map.Entry<Character, Integer> entry : map.entrySet()){
            if(entry.getValue() == 1){
                return entry.getKey();
            }
        }
        //G - 1
        //R - 1
        //E - 2
        //N -2
        //Green
        //ggeerre ->
        //fiigg ->f
        return null;
    }

    public static void main(String args[]){
        Character result = NonRepeatedCharacter("green");
        System.out.println(result);
    }
}
