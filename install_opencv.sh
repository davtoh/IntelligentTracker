#!/usr/bin/env bash
# install latest openCV 3 in python 3
# http://machinelearninguru.com/computer_vision/installation/opencv/opencv.html
# http://www.samontab.com/web/2017/06/installing-opencv-3-2-0-with-contrib-modules-in-ubuntu-16-04-lts/
# http://code.litomisky.com/2014/03/09/how-to-have-multiple-versions-of-the-same-library-side-by-side/
# https://www.pyimagesearch.com/2015/06/22/install-opencv-3-0-and-python-2-7-on-ubuntu/
# https://www.pyimagesearch.com/2015/06/29/install-opencv-3-0-and-python-3-4-on-osx/
# https://www.pyimagesearch.com/2015/07/27/installing-opencv-3-0-for-both-python-2-7-and-python-3-on-your-raspberry-pi-2/
# specify latest opencv version
version="$(wget -q -O - http://sourceforge.net/projects/opencvlibrary/files/opencv-unix | egrep -m1 -o '\"[3](\.[0-9]+)+' | cut -c2-)"
# specify the number of cores
cores=$(($(nproc) + 1))
# before installing clean build directory
clean=false
# uninstall previous installation
uninstall=false
# specify package name to install
pkgname=opencv-$version-compilation
if $uninstall; then
        sudo apt remove $pkgname -y
fi
echo "Preparing to install OpenCV" $version
# pre-requisites
echo "updating"
sudo apt-get update
sudo apt-get upgrade
echo "Installing Dependenices"
sudo apt-get -qq install build-essential checkinstall pkg-config cmake cmake-curses-gui python-dev python-numpy python-scipy python3-dev qt5-default libqt5opengl5-dev libpng3 pngtools libpng12-dev libpng12-0 libpng++-dev libtiff5-dev libtiff5 libtiff-tools libjpeg8-dev libjpeg8 libjpeg8-dbg libjasper-dev libjasper-runtime libjasper-dev libjasper-runtime libavformat-dev libavutil-dev libxine2-dev libxine2 libdc1394-22 libdc1394-22-dev libdc1394-utils libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libfaac-dev libmp3lame-dev libopencore-amrnb-dev libopencore-amrwb-dev libtheora-dev libvorbis-dev libxvidcore-dev ffmpeg x264 libx264-dev libv4l-0 v4l-utils libtbb-dev
# downloading OpenCV
if [ -f "opencv-$version.zip" ]
then
	echo "using opencv-$version.zip already in folder."
else
	echo "Downloading OpenCV" $version
	wget -O opencv-$version.zip http://sourceforge.net/projects/opencvlibrary/files/opencv-unix/$version/opencv-"$version".zip/download
	#wget -O opencv-$version.zip https://github.com/opencv/opencv/archive/"$version".zip
fi
# downloading
if [ -f "opencv_contrib-$version.zip" ]
then
	echo "using opencv_contrib-$version.zip already in folder."
else
	echo "Downloading opencv_contrib-" $version
	wget -O opencv_contrib-$version.zip https://github.com/opencv/opencv_contrib/archive/"$version".zip
fi
# installing
echo "Preparing OpenCV" $version
if [ ! -d "opencv-$version" ]; then
        unzip opencv-$version.zip
fi
if [ ! -d "opencv_contrib-$version" ]; then
        unzip opencv_contrib-$version.zip
fi
echo "Installing OpenCV" $version
cd opencv-$version
mkdir build
cd build
if $clean; then
        make clean
        cd ..
        rm -r build
        mkdir build
        cd build
fi
# to find correct python 3 path
        export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# fix -D BUILD_opencv_dnn=OFF did not work https://github.com/BVLC/caffe/issues/1917
cmake -D CMAKE_INSTALL_PREFIX=/usr/local \
        -D CMAKE_BUILD_TYPE=RELEASE \
        -D OPENCV_EXTRA_MODULES_PATH=../../opencv_contrib-$version/modules \
        -D WITH_TBB=ON \
        -D BUILD_NEW_PYTHON_SUPPORT=ON \
        -D WITH_V4L=ON \
        -D INSTALL_C_EXAMPLES=ON \
        -D INSTALL_PYTHON_EXAMPLES=ON \
        -D BUILD_EXAMPLES=ON \
        -D WITH_QT=ON \
        -D WITH_OPENGL=ON \
        -D WITH_VTK=ON ..
make -j $cores
# to create deb package and install
sudo checkinstall --pkgname $pkgname --default --nodoc
# to install directly
# sudo make install -j $cores
sudo sh -c 'echo "/usr/local/lib" > /etc/ld.so.conf.d/opencv.conf'
# keep track of shared libraries
sudo ldconfig
# exporting
#echo 'PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/usr/local/lib/pkgconfig' | sudo tee --append ~/.bashrc
#echo 'export PKG_CONFIG_PATH' | sudo tee --append ~/.bashrc
#source ~/.bashrc
cd /usr/local/lib/python3.5/dist-packages/
sudo cp cv2.cpython-35m-x86_64-linux-gnu.so cv2.so
echo "OpenCV" $version "finished"
