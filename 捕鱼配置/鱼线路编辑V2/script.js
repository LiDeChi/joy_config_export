class PathEditor {
    constructor() {
        this.canvas = document.getElementById('editor');
        this.ctx = this.canvas.getContext('2d');
        this.isFullScreen = true;
        this.points = [];
        this.isDragging = false;
        this.selectedPoint = null;
        this.animationFrame = null;
        this.isPlaying = false;
        this.fishIcon = new Image();
        this.currentTime = 0;
        
        this.initializeSize();
        this.initializePoints();
        this.initializeEventListeners();
        this.loadLastPath();
        this.initializeFavorites();
    }

    initializeSize() {
        this.updateCanvasSize();
        this.drawBaseMarker();
    }

    updateCanvasSize() {
        if (this.isFullScreen) {
            this.canvas.width = 1334 * 1;
            this.canvas.height = 750 * 1;
            this.baseWidth = 1334 * 0.5;
            this.baseHeight = 750 * 0.5;
        } else {
            this.canvas.width = 750 * 1;
            this.canvas.height = 750 * 1;
            this.baseWidth = 750 * 0.5;
            this.baseHeight = 750 * 0.5;
        }
    }

    initializePoints() {
        // 初始化3个点
        this.points = [
            {x: 2, y: 375, duration: 3},
            {x: 186, y: 153, duration: 3},
            {x: 375, y: 153, duration: 3}
        ];
        this.updateCoordinatesText();
    }

    initializeEventListeners() {
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        
        document.getElementById('toggleSize').addEventListener('click', () => {
            this.isFullScreen = !this.isFullScreen;
            this.updateCanvasSize();
            this.draw();
        });

        document.getElementById('addPoints').addEventListener('click', () => {
            const lastPoint = this.points[this.points.length - 1];
            
            let newX1 = lastPoint.x + 50;
            let newX2 = lastPoint.x + 100;
            
            if (newX2 > this.canvas.width) {
                newX1 = lastPoint.x - 50;
                newX2 = lastPoint.x - 100;
            }
            
            this.points.push(
                {x: newX1, y: lastPoint.y, duration: 3},
                {x: newX2, y: lastPoint.y, duration: 3}
            );
            this.updateCoordinatesText();
            this.draw();
            this.savePath();
        });

        document.getElementById('removePoints').addEventListener('click', () => {
            if (this.points.length > 3) {
                this.points.splice(-2);
                this.updateCoordinatesText();
                this.draw();
                this.savePath();
            }
        });

        document.getElementById('coordinatesText').addEventListener('change', (e) => {
            try {
                const data = JSON.parse(e.target.value);
                this.loadPointsFromData(data);
                this.draw();
                this.savePath();
            } catch (error) {
                console.error('坐标格式错误');
            }
        });

        document.getElementById('playAnimation').addEventListener('click', () => {
            this.startAnimation();
        });

        document.getElementById('pauseAnimation').addEventListener('click', () => {
            this.pauseAnimation();
        });

        document.getElementById('resetAnimation').addEventListener('click', () => {
            this.resetAnimation();
        });

        document.getElementById('fishIcon').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.fishIcon.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });

        document.getElementById('updatePath').addEventListener('click', () => {
            const coordText = document.getElementById('coordinatesText').value;
            try {
                const data = JSON.parse(coordText);
                this.loadPointsFromData(data);
                this.draw();
                this.savePath();
            } catch (error) {
                alert('坐标格式错误，请检查输入的JSON格式是否正确');
                console.error('坐标格式错误:', error);
            }
        });
    }

    loadPointsFromData(data) {
        this.points = [];
        data.forEach((segment, index) => {
            if (index === 0) {
                // 处理第一个数组（3个点）
                for (let i = 0; i < 6; i += 2) {
                    this.points.push({
                        x: this.realToCanvasX(segment[i]),
                        y: this.realToCanvasY(segment[i + 1]),
                        duration: segment[6]
                    });
                }
            } else {
                // 处理后续数组（2个点）
                for (let i = 0; i < 4; i += 2) {
                    this.points.push({
                        x: this.realToCanvasX(segment[i]),
                        y: this.realToCanvasY(segment[i + 1]),
                        duration: segment[4]
                    });
                }
            }
        });
    }

    updateCoordinatesText() {
        const textArea = document.getElementById('coordinatesText');
        const formattedData = this.formatPointsData();
        textArea.value = JSON.stringify(formattedData);
    }

    formatPointsData() {
        const result = [];
        // 第一个子数组包含前3个点的坐标
        let firstSegment = [
            this.canvasToRealX(this.points[0].x),
            this.canvasToRealY(this.points[0].y),
            this.canvasToRealX(this.points[1].x),
            this.canvasToRealY(this.points[1].y),
            this.canvasToRealX(this.points[2].x),
            this.canvasToRealY(this.points[2].y),
            this.points[2].duration
        ];
        result.push(firstSegment);
        
        // 从第3个点开始，每次取两个点作为一个子数组
        for (let i = 3; i < this.points.length - 1; i += 2) {
            const segment = [
                this.canvasToRealX(this.points[i].x),
                this.canvasToRealY(this.points[i].y),
                this.canvasToRealX(this.points[i + 1].x),
                this.canvasToRealY(this.points[i + 1].y),
                this.points[i + 1].duration
            ];
            result.push(segment);
        }
        
        return result;
    }

    draw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawBaseMarker();
        this.drawBezierCurve();
        this.drawPoints();
    }

    drawBaseMarker() {
        const marker = document.querySelector('.base-size-marker');
        marker.style.width = `${this.baseWidth}px`;
        marker.style.height = `${this.baseHeight}px`;
        marker.style.left = `${(this.canvas.width - this.baseWidth) / 2}px`;
        marker.style.top = `${(this.canvas.height - this.baseHeight) / 2}px`;

        // 添加坐标轴和刻度
        const offsetX = (this.canvas.width - this.baseWidth) / 2;
        const offsetY = (this.canvas.height + this.baseHeight) / 2;
        
        // 绘制坐标轴
        this.ctx.beginPath();
        this.ctx.strokeStyle = '#666';
        this.ctx.lineWidth = 1;
        
        // X轴
        this.ctx.moveTo(offsetX, offsetY);
        this.ctx.lineTo(offsetX + this.baseWidth, offsetY);
        
        // Y轴
        this.ctx.moveTo(offsetX, offsetY);
        this.ctx.lineTo(offsetX, offsetY - this.baseHeight);
        this.ctx.stroke();

        // 绘制刻度
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'top';
        this.ctx.fillStyle = '#666';
        this.ctx.font = '12px Arial';

        // X轴刻度 (向右为正)
        const xStep = this.baseWidth / 10;
        for (let x = 0; x <= this.baseWidth; x += xStep) {
            // 根据当前模式选择正确的基准宽度
            const maxWidth = this.isFullScreen ? 1334 : 750;
            const realX = Math.round((x * maxWidth) / this.baseWidth);
            
            this.ctx.beginPath();
            this.ctx.moveTo(offsetX + x, offsetY);
            this.ctx.lineTo(offsetX + x, offsetY + 5);
            this.ctx.stroke();
            this.ctx.fillText(realX.toString(), offsetX + x, offsetY + 8);
        }

        // Y轴刻度 (向上为正)
        const yStep = this.baseHeight / 10;
        this.ctx.textAlign = 'right';
        this.ctx.textBaseline = 'middle';
        for (let y = 0; y <= this.baseHeight; y += yStep) {
            // 半屏和全屏的高度都是750
            const realY = Math.round((y * 750) / this.baseHeight);
            const yPos = offsetY - y;
            
            this.ctx.beginPath();
            this.ctx.moveTo(offsetX - 5, yPos);
            this.ctx.lineTo(offsetX, yPos);
            this.ctx.stroke();
            this.ctx.fillText(realY.toString(), offsetX - 8, yPos);
        }
    }

    drawBezierCurve() {
        this.ctx.beginPath();
        this.ctx.moveTo(this.points[0].x, this.points[0].y);
        
        for (let i = 1; i < this.points.length; i += 2) {
            const cp = this.points[i];
            const end = this.points[i + 1] || this.points[i];
            this.ctx.quadraticCurveTo(cp.x, cp.y, end.x, end.y);
        }
        
        this.ctx.strokeStyle = '#333';
        this.ctx.stroke();
    }

    drawPoints() {
        this.points.forEach((point, index) => {
            // 绘制点
            this.ctx.beginPath();
            this.ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
            this.ctx.fillStyle = index % 2 === 0 ? '#f00' : '#00f';
            this.ctx.fill();

            // 在蓝色控制点旁边显示时间
            if (index % 2 === 1) {  // 蓝色控制点
                this.ctx.font = '14px Arial';
                this.ctx.fillStyle = '#333';
                this.ctx.textAlign = 'left';
                this.ctx.textBaseline = 'middle';
                
                // 在点的右侧显示时间
                const timeText = `${point.duration}s`;
                this.ctx.fillText(timeText, point.x + 10, point.y);
            }
        });
    }

    startAnimation() {
        if (!this.isPlaying) {
            this.isPlaying = true;
            this.animate();
        }
    }

    pauseAnimation() {
        this.isPlaying = false;
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }

    resetAnimation() {
        this.currentTime = 0;
        this.pauseAnimation();
        this.draw();
    }

    animate() {
        if (!this.isPlaying) return;

        this.draw();
        
        // 计算鱼的位置
        const position = this.calculateFishPosition(this.currentTime);
        if (position) {
            this.drawFish(position.x, position.y, position.angle);
        }

        this.currentTime += 0.016; // 约60fps
        this.animationFrame = requestAnimationFrame(this.animate.bind(this));
    }

    calculateFishPosition(time) {
        // 计算鱼在曲线上的位置和角度
        // 这里需要根据时间和贝塞尔曲线计算具体位置
        // 返回 {x, y, angle}
    }

    drawFish(x, y, angle) {
        if (this.fishIcon.complete) {
            this.ctx.save();
            this.ctx.translate(x, y);
            this.ctx.rotate(angle);
            this.ctx.drawImage(this.fishIcon, -20, -20, 40, 40);
            this.ctx.restore();
        }
    }

    handleMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.points.forEach((point, index) => {
            const dx = point.x - x;
            const dy = point.y - y;
            if (dx * dx + dy * dy < 25) {
                this.isDragging = true;
                this.selectedPoint = index;
            }
        });
    }

    handleMouseMove(e) {
        if (!this.isDragging) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // 直接使用鼠标位置，不做限制
        this.points[this.selectedPoint].x = x;
        this.points[this.selectedPoint].y = y;
        
        this.updateCoordinatesText();
        this.draw();
        this.savePath();
    }

    handleMouseUp() {
        this.isDragging = false;
        this.selectedPoint = null;
    }

    canvasToRealY(canvasY) {
        const offsetY = (this.canvas.height + this.baseHeight) / 2;
        return Math.round((offsetY - canvasY) * (750 / this.baseHeight)); // 转换为750坐标系
    }

    realToCanvasY(realY) {
        const offsetY = (this.canvas.height + this.baseHeight) / 2;
        return offsetY - (realY * (this.baseHeight / 750)); // 从750坐标系转换回来
    }

    canvasToRealX(canvasX) {
        const offsetX = (this.canvas.width - this.baseWidth) / 2;
        const maxWidth = this.isFullScreen ? 1334 : 750;
        return Math.round((canvasX - offsetX) * (maxWidth / this.baseWidth));
    }

    realToCanvasX(realX) {
        const offsetX = (this.canvas.width - this.baseWidth) / 2;
        const maxWidth = this.isFullScreen ? 1334 : 750;
        return offsetX + (realX * (this.baseWidth / maxWidth));
    }

    savePath() {
        const pathData = {
            points: this.points,
            isFullScreen: this.isFullScreen
        };
        localStorage.setItem('lastPath', JSON.stringify(pathData));
    }

    loadLastPath() {
        const savedPath = localStorage.getItem('lastPath');
        if (savedPath) {
            const pathData = JSON.parse(savedPath);
            this.points = pathData.points;
            this.isFullScreen = pathData.isFullScreen;
            this.updateCanvasSize();
            this.updateCoordinatesText();
            this.draw();
        }
    }

    initializeFavorites() {
        // 初始化收藏相关的事件监听
        document.getElementById('saveFavorite').addEventListener('click', () => {
            this.saveFavorite();
        });

        // 初始显示收藏列
        this.displayFavorites();
    }

    saveFavorite() {
        const name = document.getElementById('pathName').value.trim();
        if (!name) {
            alert('请输入路线名称');
            return;
        }

        // 获取当前路线数据
        const pathData = {
            name: name,
            points: this.points,
            isFullScreen: this.isFullScreen,
            timestamp: Date.now()
        };

        // 从localStorage获取现有收藏
        let favorites = JSON.parse(localStorage.getItem('pathFavorites') || '[]');
        
        // 检查是否存在同名路线
        const existingIndex = favorites.findIndex(f => f.name === name);
        if (existingIndex >= 0) {
            if (!confirm('已存在同名路线，是否覆盖？')) {
                return;
            }
            favorites[existingIndex] = pathData;
        } else {
            favorites.push(pathData);
        }

        // 保存到localStorage
        localStorage.setItem('pathFavorites', JSON.stringify(favorites));
        
        // 清空输入框并刷新显示
        document.getElementById('pathName').value = '';
        this.displayFavorites();
    }

    displayFavorites() {
        const favorites = JSON.parse(localStorage.getItem('pathFavorites') || '[]');
        const listElement = document.getElementById('favoriteList');
        listElement.innerHTML = '';

        favorites.forEach(favorite => {
            const item = document.createElement('div');
            item.className = 'favorite-item';
            
            const nameSpan = document.createElement('span');
            nameSpan.textContent = favorite.name;
            nameSpan.className = 'favorite-name';
            
            const loadButton = document.createElement('button');
            loadButton.textContent = '加载';
            loadButton.onclick = () => this.loadFavorite(favorite);
            
            const deleteButton = document.createElement('button');
            deleteButton.textContent = '删除';
            deleteButton.onclick = () => this.deleteFavorite(favorite.name);

            item.appendChild(nameSpan);
            item.appendChild(loadButton);
            item.appendChild(deleteButton);
            listElement.appendChild(item);
        });
    }

    loadFavorite(favorite) {
        this.points = favorite.points;
        this.isFullScreen = favorite.isFullScreen;
        this.updateCanvasSize();
        this.updateCoordinatesText();
        this.draw();
        this.savePath(); // 保存为当前路径
    }

    deleteFavorite(name) {
        if (!confirm(`确定要删除路线"${name}"吗？`)) {
            return;
        }

        let favorites = JSON.parse(localStorage.getItem('pathFavorites') || '[]');
        favorites = favorites.filter(f => f.name !== name);
        localStorage.setItem('pathFavorites', JSON.stringify(favorites));
        
        this.displayFavorites();
    }
}

// 初始化编辑器
window.addEventListener('load', () => {
    new PathEditor();
}); 