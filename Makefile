run: png
	python animate.py \
		--repeat \
		--actor dist/actor.png \
		--background dist/background1.png

movie: png
	mkdir -p dist/frames
	rm -f dist/frames/* \
		&& python animate.py \
			--no-gui \
			--actor dist/actor.png \
			--background dist/background1.png \
			--output 'dist/frames/frame%04d.bmp'
	ffmpeg -y -r 60 -i dist/frames/frame%4d.bmp dist/movie.webm

# assets/blinker.svg requires manually exporting layers for now
#		--actor dist/blinker0.png \
#		--actor dist/blinker1.png \
#		--actor dist/blinker2.png \

png: dist/actor.png dist/background1.png

dist/actor.png: assets/box.svg
	mkdir -p dist
	inkscape --export-area-drawing -o dist/actor.png assets/box.svg

dist/background1.png: assets/background1.svg
	mkdir -p dist
	inkscape --export-id=background -o dist/background1.png assets/background1.svg

clean:
	rm dist/actor.png dist/background1.png
