// Bjorn Wesen 2014

#include <stdio.h>
#include <math.h>
#include <stdlib.h>

int numpoints, numcvs;


float
dist(const float *v1, const float *v2)
{
        //return sum([x**2 for x in map(sub, v1, v2)])**(.5)

        float sum2 = 0.0f;
        for(int x = 0; x < numcvs; x++) {
                float s = v2[x] - v1[x];
                sum2 += s * s;
        }
        
        return sqrtf(sum2);
}


// path length upto the nth interpolant
// 1-based indexing following Maragliano

float
rep_L(int n, float **path)
{
        if(n == 0)
                return 1.0f;
        
        float pathlength = 0.0f;
        for(int i = 0; i < (n - 1); i++)
                pathlength += dist(path[i], path[i + 1]);

        return pathlength;
}

float
rep_s(int m, float **path)
{
        int R = numpoints - 1;
        return (m - 1) * rep_L(R, path) / (float)(R - 1);
}

// Calculate a normalized "direction" from v1 to v2. Result in normed.

void
dir(const float *v1, const float *v2, float *normed)
{
        float d = dist(v1, v2);
        if(d == 0.0f) {
                // this case should not really happen..
                fprintf(stderr, "Rep dir had a dist = 0.0. This should not be possible.\n");
                d = 0.0001f;
        }

        for(int i = 0; i < numcvs; i++)
                normed[i] = (v2[i] - v1[i]) / d;
}

int
main(int argc, char **argv)
{
        char buf[512];
        fgets(buf, 511, stdin);

        // Get the number of points and CVs passed on as the first 2 numbers on stdin

        if(sscanf(buf, "%d %d", &numpoints, &numcvs) != 2) {
                fprintf(stderr, "Couldn't read number of points or CVs from the main process\n");
                return 1;
        }
        
        // Create and read the path-array from stdin in its flattened format

        float **points = (float **)malloc(sizeof(float *) * numpoints);
        
        for(int p = 0; p < numpoints; p++) {
                points[p] = (float *)malloc(sizeof(float *) * numcvs);
                for(int c = 0; c < numcvs; c++) {
                        float val;
                        fgets(buf, 511, stdin);
                        if(sscanf(buf, "%f", &val) == 1) {
                                float *point = points[p];
                                point[c] = val;
                        }
                        
                }
        }
                        
        // Reparametrize the points
        // See Maragliano et al, J. Chem Phys (125), 2006
        // We use a linear interpolation in Euclidean space adjusted to ensure equidistance points

        float **adjusted = (float **)malloc(sizeof(float *) * numpoints);
        // First and last stay the same
        adjusted[0] = points[0];
        adjusted[numpoints - 1] = points[numpoints - 1];
        
        for(int i = 2; i < numpoints; i++) {
                float Lk_m1, si;
                // Do the while-loop like this, since we re-use part of the calculations here further
                // below and don't waste time calling them multiple times
                int k = 1;
                do {
                        k++;
                        Lk_m1 = rep_L(k - 1, points);
                        si = rep_s(i, points);
                } while(Lk_m1 >= si || si > rep_L(k, points));

                float v[numcvs];
                dir(points[k - 2], points[k - 1], v);
                adjusted[i - 1] = (float *)malloc(sizeof(float *) * numcvs);
                float *reppt = adjusted[i - 1];
                float scalefactor = si - Lk_m1;
                const float *inppt = points[k - 2];
                for(int x = 0; x < numcvs; x++)
                        reppt[x] = inppt[x] + v[x] * scalefactor;
        }

        // Output all data as a flat file to stdout with \n between each number
        
        for(int p = 0; p < numpoints; p++) {
                float *adjpoint = adjusted[p];
                for(int c = 0; c < numcvs; c++) {
                        printf("%f\n", adjpoint[c]);
                }
        }

        // Note: we don't bother to cleanup and free the arrays, since we exit the program here anyway.
        // But take care to do that if we ever re-use this code somehow.

        return 0;
}
