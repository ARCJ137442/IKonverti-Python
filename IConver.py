from PIL import Image
import math
import os
import traceback
from tqdm import tqdm

'''
Binary to image:
     1.Convert byte array to 32-bit pixel int array
         For example: [0xff,0x76,0x00,0x3a,0x98,0x1d,0xcb] (len=7)-> [0xff76003a,0x981dcb00] (len=2)
     2.Insert the length pixel (len (byte)% 4,0x1 in the example) in the first bit of the int array
     3. Create a picture from an int array
Image to binary:
     1.Convert image to array of length L and 32-bit pixel int
         For example: L=3,[0x998acb6a,0x6a634bde,0x87000000]
     2.Convert 32-bit pixel int array to byte array
         For example: [0x998acb6a,0x6a634bde,0x87000000]-> [0x99,0x8a,0xcb,0x6a,0x6a,0x63,0x4b,0xde,0x87,0x00,0x00,0x00]
     3. Delete the L elements at the end of the byte array
         For example: [0x99,0x8a,0xcb,0x6a,0x6a,0x63,0x4b,0xde,0x87,0x00,0x00,0x00]-> [0x99,0x8a,0xcb,0x6a,0x6a,0x63,0x4b,0xde,0x87]
     4. Create binary file based on byte array

二进制转图像：
    1.把byte数组转换为32位像素int数组
        例如：[0xff,0x76,0x00,0x3a,0x98,0x1d,0xcb](len=7) -> [0xff76003a,0x981dcb00](len=2)
    2.在int数组第一位插入长度像素(len(byte)%4,例中为0x1)
    3.根据int数组创建图片
图像转二进制：
    1.把图像转换为长度L和32位像素int数组
        例如：L=3,[0x998acb6a,0x6a634bde,0x87000000]
    2.把32位像素int数组转换为byte数组
        例如：[0x998acb6a,0x6a634bde,0x87000000] -> [0x99,0x8a,0xcb,0x6a,0x6a,0x63,0x4b,0xde,0x87,0x00,0x00,0x00]
    3.删除byte数组末尾的L个元素
        例如：[0x99,0x8a,0xcb,0x6a,0x6a,0x63,0x4b,0xde,0x87,0x00,0x00,0x00] -> [0x99,0x8a,0xcb,0x6a,0x6a,0x63,0x4b,0xde,0x87]
    4.根据byte数组创建二进制文件
'''

DEBUG=True
NCOLS=70

#aa,rr,gg,bb -> 0xaarrggbb
def binaryToPixels(binary):#bytes b
    global NCOLS
    binaryLength=len(binary)
    result=[(-binaryLength)&3]#included length,4 bit in a pixel
    j=0
    pixel=0
    for i in tqdm(range(binaryLength),desc='Converting: ',ncols=NCOLS):
        if j<4:pixel|=binary[i]<<(j<<3)
        else:
            j=0
            result.append(pixel)
            pixel=binary[i]
        j=j+1
    if j!=0:result.append(pixel)#Add the end of byte
    return result
#returns int[]

#0xaarrggbb -> aa,rr,gg,bb
def pixelsToBinary(pixels):#int[] pixels
    result=[]
    processBar=tqdm(total=len(pixels),desc='Converting: ',ncols=NCOLS)
    for pixel in pixels:
        result.append(pixel&0xff)#b
        result.append((pixel&0xff00)>>8)#g
        result.append((pixel&0xff0000)>>16)#r
        result.append((pixel&0xff000000)>>24)#a
        processBar.update(1)
    processBar.close()
    return result
#returns bytes

#0=binary,1=image,-1=exception
def readFile(path):
    try:
        file0=readImage(path)
        if file0==None:
            file0=readBinary(path)
            if file0==None:return (-1,FileNotFoundError(path))
            return (0,file0)
        else:return (1,file0)
    except BaseException as error:return (-1,error)

def autoConver(currentFile,forceImage=False):
    #====Define====#
    if currentFile!=None:
        try:dealFromImage(currentFile,file_path)
        except BaseException as e:printExcept(e,"autoConver()->")
        else:return
    if (not forceImage) and type(currentFile)!='image':print("Faild to load image \""+file_path+"\",now try to load as binary")
    currentFile=readBinary(path)
    dealFromBinary(file_path,currentFile)

def dealFromBinary(path,binaryFile):
    #========From Binary========#
    if binaryFile==None:
        print("Faild to load binary \""+path+"\"")
        return
    print("PATH:"+path+",FILE:",binaryFile)
    #====1 Convert Binary and 2 Insert Pixel====#
    pixels=binaryToPixels(binaryFile.read())
    #====Close File====#
    binaryFile.close()
    #====3 Create Image====#
    createImage(path,pixels)

def dealFromImage(imageFile,path):
    print("PATH:"+path+",FILE:",imageFile,imageFile.format)
    #========From Image========#
    #====1 Convert Image to Pixel,and Get Length====#
    PaL=getPixelsAndLength(imageFile)
    tailLength=PaL[0]&3#Limit the length lower than 4
    pixels=PaL[1]
    #====2 Convert Pixel to Binary and 3 Delete the L Byte====#
    binary=pixelsToBinary(pixels)
    if tailLength>0:
        for i in range(tailLength):binary.pop()
    #====4 Create Binary File====#
    imageFile.close()
    createBinaryFile(bytes(binary),path)

def getPixelsAndLength(image):
    global NCOLS
    result=[0,[]]
    isFirst=True
    pixList=list(image.getdata())
    processBar=tqdm(total=len(pixList),desc='Scanning: ',ncols=NCOLS)
    for pixel in pixList:
        color=RGBAtoPixel(pixel)
        if isFirst:
            result[0]=color
            isFirst=False
        else:result[1].append(color)
        processBar.update(1)
    processBar.close()
    return result
#returns (int,int[])

def createImage(sourcePath,pixels):
    global NCOLS
    global DEBUG
    #==Operate Image==#
    lenPixel=len(pixels)
    width=int(math.sqrt(lenPixel))
    while lenPixel%width>0:width=width-1
    height=int(lenPixel/width)
    nImage=Image.new("RGBA",(width,height),(0,0,0,0))
    i=0
    niLoad=nImage.load()
    processBar=tqdm(total=lenPixel,desc='Creating: ',ncols=NCOLS)
    for y in range(height):
        for x in range(width):
            #==Write Image==#old:nim.putpixel((x,y),pixelToRGBA(pixels[i]))
            niLoad[x,y]=RGBAtoBGRA(pixels[i])#The image's load need write pixel as 0xaabbggrr,I don't know why
            i=i+1
            processBar.update(1)
    processBar.close()
    #==Save Image==#
    #Show Image(Unused) #nim.show()
    nImage.save(os.path.basename(sourcePath)+'.png')
    if DEBUG:print(nImage,nImage.format)
    print("Image File created!")

#For pixel: 0xaarrggbb -> 0xaabbggrr
def RGBAtoBGRA(pixel):return ((pixel&0xff0000)>>16)|((pixel&0xff)<<16)|(pixel&0xff00ff00)

def createBinaryFile(binary,path):#bytes binary,str path
    #Build Text
    try:
        file=open(generateFileName(path),'wb',-1)
        file.write(binary)
    except BaseException as exception:printExcept(exception,"createBinaryFile()->")
    #==Close File==#
    file.close()
    print("Binary File generated!")

#pixel(0xaarrggbb) -> RGBA(r,g,b,a)
def pixelToRGBA(pixel):return ((pixel>>16)&0xff,(pixel>>8)&0xff,pixel&0xff,(pixel>>24))

#RGBA(a,r,g,b)<Tuple/List> -> pixel(0xaarrggbb)
def RGBAtoPixel(color):
    #For Image uses RGB:
    if len(color)<4:alpha=0xff000000
    else:alpha=color[3]<<24
    return alpha|(color[0]<<16)|(color[1]<<8)|color[2]

def generateFileName(originPath):
    baseName=os.path.basename(originPath)
    if baseName.count('.')>1:return baseName[0:baseName.rindex('.')]
    return baseName+'.txt'

def readImage(path):
    try:return Image.open(path)
    except:return None

def readBinary(path):return open(path,'rb')#raises error

def printExcept(exc,funcPointer):
    global DEBUG
    if DEBUG:print(funcPointer+"Find a exception:",exc,"\n"+traceback.format_exc())
    else: print(funcPointer+"Find a exception:",exc)

def InputYN(head):
    yn=input(head)
    return yn.lower()=="y" or yn.lower()=="yes" or yn.lower()=="true"

#Function Main
if __name__=='__main__':
    import sys
    if len(sys.argv) > 1:
        for file_path in sys.argv[1:]:
            autoConver(file_path)
            print()
    else:
        print("<====IConver====>")
        #print("Now in Command Line Mode!")
        while(True):
            try:
                #print("Usage: python IConver.py \"File Name\"")
                path=input("Please choose PATH:")
                fileImf=readFile(path)
                code_=fileImf[0]
                file_=fileImf[1]
                if code_==0 or (code_>0 and InputYN("Force compress to Image?Y/N:")):dealFromBinary(path,file_)
                elif code_>0:dealFromImage(file_,path)
                else:raise file_#exception at here
            except BaseException as e:
                printExcept(e,"readText()->")
                if InputYN("Do you want to terminate the program?Y/N:"):break
            print()#new line