p0 = [-20,0];
p1 = [-30,0];
p2 = [-30,10];
p3 = [-28,15];
p4 = [-30,20];
p5 = [-30,50];
p6 = [-20,50];
p7 = [-20,20];
p8 = [-22,15];
p9 = [-20,10];

l_points = [p0,p1,p2,p3,p4,p5,p6,p7,p8,p9];
i_points = [p0,p6,[20,50],[20,0]];

module base_geo(l_points,i_points){

translate([0,0,-10])
linear_extrude(height=20,twist=0){
    
    {polygon(l_points);

translate([50,0,0]) polygon(l_points);

difference() {
    translate([0,50,0]) circle(30);
    translate([0,50,0]) circle(20);
    polygon(i_points);
}

};
};
};


//datum features

lld = [-31,25,0];
lud = [-31,45,0];
rld = [26,25,0];
rud = [26,45,0];

d = [lld,lud,rld,rud];

module main_geo(d){
difference(){
difference(){
base_geo(l_points,i_points);
    translate([0,15,0])
    rotate([0,90,0])
    union(){
    linear_extrude(height=100,twist=0) circle(5);
    rotate([0,180,0]) linear_extrude(height=100,twist=0) circle(5);
    };
for (i = [0:len(d)-1]){
        translate(d[i]) rotate([0,90,0]) linear_extrude(height=5, twist = 0) circle(1);
    };
}
}
}

//run with argument "d" to get datum features
main_geo(d);

