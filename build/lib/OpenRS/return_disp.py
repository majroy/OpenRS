import numpy as np


def get_disp_from_fid(*args):
    '''
    From incoming numpy array of 4 fiducial points, return displacement for FEA model
    '''
    
    #test centers of fiducial points
    pts = args[0]
    
    def normalize(v):
        norm=np.linalg.norm(v)
        if norm==0:
            norm=np.finfo(v.dtype).eps
        return v/norm

    #original points at nominal positions prior to bending
    o_pts = np.array([[-28,15,0],[28,15,0]])#according to nominal dimensions
    nom_dist = np.linalg.norm(o_pts[0,:]-o_pts[1,:]) #distance between notches

    #move all points to center on 0,0,0
    pts = pts - pts.mean(axis=0)
    o_pts = o_pts - o_pts.mean(axis=0)

    #build vectors of 'rotated' coordinate system
    a = normalize((pts[1,:]+pts[2,:])/2 - (pts[0,:]+pts[3,:])/2)
    cs_r = np.array([normalize(pts[3,:]-pts[0,:]),
    a,
    normalize(np.cross(normalize(pts[3,:]-pts[0,:]),a))
    ])
    #non-rotated system
    cs = np.eye(3)

    R = np.dot(np.linalg.inv(cs_r),cs)
    n_pts = np.dot(pts,R) #rotate from measured position back to principal Cartesian system


    #now create new 'virtual' notch locations from n_pts
    #left side
    l_norm = normalize(n_pts[0,:]-n_pts[1,:])
    pt = n_pts[1,:]+l_norm*30 #distance from F2 to centre of notch
    l_in = normalize(np.cross(l_norm,np.array([0,0,1])))
    pt_notch1 = pt+l_in*(-12) #from stylus length to depth of notch


    #right side
    r_norm = normalize(n_pts[3,:]-n_pts[2,:])
    npt = n_pts[2,:]+r_norm*30
    r_in = normalize(np.cross(r_norm,np.array([0,0,1])))
    pt_notch2 = npt+r_in*12

    dist = np.linalg.norm(pt_notch1-pt_notch2)

    if args[1]:
        #set up plotting
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        plt.scatter(pts[:,0], pts[:,1], color='g') #plot x,y of incoming points
        plt.scatter(n_pts[:,0], n_pts[:,1], color='b') #plot transformed incoming points
        #plot the construction of virtual points (back to one of the notches)
        ax.plot([n_pts[1,0], pt[0], pt_notch1[0]], [n_pts[1,1], pt[1], pt_notch1[1]], 'c')
        #plot notch centres
        plt.scatter(pt_notch1[0], pt_notch1[1], color='c', s=3)
        plt.scatter(pt_notch2[0], pt_notch2[1], color='c', s=3)
        ax.set_aspect('equal')
        plt.show()
        
    return nom_dist-dist

if __name__ == '__main__':
    #demonstrate with a randomly transformed set of deformed fiducial points
    pts = np.array([[-27.84974149,   8.25648299, -27.14252199],
     [-14.17425371,  20.42276913, -35.26616725],
     [ 37.1098363,   -0.29734781,  22.01075151],
     [ 23.17469854, -12.35872062,  29.84442142]])
    d = get_disp_from_fid(pts,True)
    print(d)