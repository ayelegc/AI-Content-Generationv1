.PHONY: film clean

film:
	python3 pipeline/run_pipeline.py --stage all

radio-cut:
	python3 pipeline/run_pipeline.py --stage script
	python3 pipeline/run_pipeline.py --stage narration
	python3 pipeline/run_pipeline.py --stage music

clean:
	rm -rf outputs/.cache outputs/keyframes/* outputs/shots/* outputs/music/* outputs/narration/* outputs/final/*.mp4 outputs/final/*.srt outputs/final/_work
